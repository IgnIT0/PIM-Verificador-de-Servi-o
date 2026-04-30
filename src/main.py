import tkinter as tk
from tkinter import messagebox, ttk
import threading
import datetime
from modulo import Service, Notifier, Storage, NetworkMapper

class UptimeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor de Infraestrutura Pro - Sistema de Gestão de Ativos")
        self.root.geometry("1100x750")
        
        # --- PALETA DE CORES (DARK MODE PROFISSIONAL) ---
        self.colors = {
            "bg": "#121212",
            "card": "#1e1e1e",
            "fg": "#e0e0e0",
            "accent": "#6200ee",
            "success": "#03dac6",
            "danger": "#cf6679",
            "warning": "#ffb74d",
            "border": "#333333"
        }
        self.root.configure(bg=self.colors["bg"])
        
        # Inicialização dos Módulos
        self.notifier = Notifier()
        self.storage = Storage()
        self.mapper = NetworkMapper()
        self.services = []

        # Configuração de Estilo ttk
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Treeview", 
                             background=self.colors["card"], 
                             foreground=self.colors["fg"], 
                             fieldbackground=self.colors["card"], 
                             rowheight=35, 
                             borderwidth=0,
                             font=("Segoe UI", 10))
        self.style.map("Treeview", background=[('selected', self.colors["accent"])])
        self.style.configure("Treeview.Heading", 
                             background=self.colors["border"], 
                             foreground=self.colors["fg"], 
                             font=("Segoe UI", 10, "bold"))

        # --- ÁREA DE COMANDOS (CADASTRO) ---
        frame_add = tk.LabelFrame(root, text=" Adicionar Novo Ativo ", bg=self.colors["bg"], 
                                  fg=self.colors["fg"], padx=15, pady=15, font=("Segoe UI", 10, "bold"))
        frame_add.pack(fill="x", padx=20, pady=10)

        # Labels e Entrys
        tk.Label(frame_add, text="Nome/Apelido:", bg=self.colors["bg"], fg=self.colors["fg"]).grid(row=0, column=0, padx=5)
        self.ent_name = tk.Entry(frame_add, width=18, bg=self.colors["card"], fg="white", insertbackground="white")
        self.ent_name.grid(row=0, column=1, padx=5)

        tk.Label(frame_add, text="Alvo (IP/URL):", bg=self.colors["bg"], fg=self.colors["fg"]).grid(row=0, column=2, padx=5)
        self.ent_target = tk.Entry(frame_add, width=25, bg=self.colors["card"], fg="white", insertbackground="white")
        self.ent_target.grid(row=0, column=3, padx=5)

        tk.Label(frame_add, text="Protocolo:", bg=self.colors["bg"], fg=self.colors["fg"]).grid(row=0, column=4, padx=5)
        self.combo_proto = ttk.Combobox(frame_add, values=["HTTP", "ICMP"], width=8, state="readonly")
        self.combo_proto.current(0)
        self.combo_proto.grid(row=0, column=5, padx=5)

        # Botões de Ação
        tk.Button(frame_add, text="ADICIONAR", command=self.add_service, 
                  bg=self.colors["success"], fg="black", font=("Segoe UI", 9, "bold"), width=12).grid(row=0, column=6, padx=10)
        
        tk.Button(frame_add, text="EDITAR", command=self.edit_service, 
                  bg=self.colors["warning"], fg="black", font=("Segoe UI", 9, "bold"), width=10).grid(row=0, column=7, padx=5)
        
        tk.Button(frame_add, text="REMOVER", command=self.remove_service, 
                  bg=self.colors["danger"], fg="white", font=("Segoe UI", 9, "bold"), width=10).grid(row=0, column=8, padx=5)

        # --- VISUALIZAÇÃO HIERÁRQUICA (TREEVIEW) ---
        container_tree = tk.Frame(root, bg=self.colors["bg"])
        container_tree.pack(fill="both", expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(container_tree, columns=("tipo", "status", "latencia", "visto"), show="tree headings")
        
        # Definição de Cabeçalhos
        self.tree.heading("#0", text="ESTRUTURA DE REDE / ATIVOS")
        self.tree.heading("tipo", text="IDENTIFICAÇÃO")
        self.tree.heading("status", text="STATUS")
        self.tree.heading("latencia", text="LATÊNCIA")
        self.tree.heading("visto", text="ÚLTIMA VERIFICAÇÃO")

        # Configuração de Colunas
        self.tree.column("#0", width=300, anchor="w")
        self.tree.column("tipo", width=150, anchor="center")
        self.tree.column("status", width=130, anchor="center")
        self.tree.column("latencia", width=100, anchor="center")
        self.tree.column("visto", width=200, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(container_tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Inicialização de dados e loop
        self.load_saved_data()
        self.update_loop()

    def add_service(self, name=None, target=None, protocol=None, parent=""):
        """Adiciona um serviço à lista e à árvore visual."""
        name = name or self.ent_name.get().strip()
        target = target or self.ent_target.get().strip()
        protocol = protocol or self.combo_proto.get()

        if not name or not target:
            if not parent: messagebox.showwarning("Aviso", "Preencha Nome e Alvo.")
            return

        # Verifica duplicidade
        if any(s.name == name for s in self.services):
            if not parent: messagebox.showwarning("Erro", "Já existe um serviço com este nome.")
            return

        novo = Service(name, target, protocol)
        self.services.append(novo)
        
        # Insere na árvore (iid é o nome para referência única)
        self.tree.insert(parent, "end", iid=name, text=f"  {name}", 
                         values=(novo.ip_version, "⏳ Aguardando", "--", "--"))
        
        # Se for um novo servidor principal (sem pai), tenta mapear vizinhos
        if not parent and novo.ip_version in ["IPv4", "IPv6"]:
            threading.Thread(target=self.auto_discover_task, args=(novo,), daemon=True).start()

        # Persistência apenas para itens principais (pais)
        if not parent:
            self.storage.save_services_config(self.services)
            self.ent_name.delete(0, tk.END)
            self.ent_target.delete(0, tk.END)

    def auto_discover_task(self, parent_service):
        """Busca dispositivos vizinhos e os pendura na hierarquia."""
        neighbors = self.mapper.discover_neighbors(parent_service.target)
        for n in neighbors:
            # Verifica se já não monitoramos este IP
            if not any(s.target == n['ip'] for s in self.services):
                self.root.after(0, self.add_service, n['ip'], n['ip'], "ICMP", parent_service.name)
                # Atualiza o tipo detectado (ex: Impressora) na árvore
                self.root.after(500, lambda ip=n['ip'], t=n['type']: self.tree.set(ip, "tipo", t))

    def edit_service(self):
        """Abre popup para renomear ou alterar alvo do serviço selecionado."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione um item para editar.")
            return
        
        item_id = selected[0]
        service_obj = next((s for s in self.services if s.name == item_id), None)
        if not service_obj: return

        # Janela Popup de Edição
        pop = tk.Toplevel(self.root)
        pop.title("Editar Ativo")
        pop.geometry("400x250")
        pop.configure(bg=self.colors["card"])
        pop.transient(self.root) # Abre sobre a main
        pop.grab_set()

        tk.Label(pop, text=f"Editando: {item_id}", bg=self.colors["card"], fg=self.colors["success"], font=("bold")).pack(pady=10)
        
        tk.Label(pop, text="Novo Nome:", bg=self.colors["card"], fg="white").pack()
        new_n = tk.Entry(pop, width=35); new_n.insert(0, service_obj.name); new_n.pack(pady=5)
        
        tk.Label(pop, text="Novo Alvo (IP/URL):", bg=self.colors["card"], fg="white").pack()
        new_t = tk.Entry(pop, width=35); new_t.insert(0, service_obj.target); new_t.pack(pady=5)

        def save_edit():
            name_val = new_n.get().strip()
            target_val = new_t.get().strip()
            if name_val and target_val:
                parent = self.tree.parent(item_id)
                service_obj.update_info(name_val, target_val) # Método adicionado no modulo.py
                self.tree.delete(item_id)
                self.tree.insert(parent, "end", iid=name_val, text=f"  {name_val}", 
                                 values=(service_obj.ip_version, "⏳ Atualizando", "--", "--"))
                self.storage.save_services_config(self.services)
                pop.destroy()

        tk.Button(pop, text="CONFIRMAR ALTERAÇÕES", command=save_edit, bg=self.colors["accent"], fg="white").pack(pady=20)

    def remove_service(self):
        selected = self.tree.selection()
        if not selected: return
        if messagebox.askyesno("Confirmar", "Deseja remover o(s) item(s) selecionado(s)?"):
            for item in selected:
                self.services = [s for s in self.services if s.name != item]
                self.tree.delete(item)
            self.storage.save_services_config(self.services)

    def load_saved_data(self):
        """Carrega os dados persistidos do JSON."""
        data = self.storage.load_services_config()
        for item in data:
            self.add_service(item['name'], item['target'], item.get('protocol', 'HTTP'))

    def run_check(self, service):
        """Executa a verificação e atualiza a interface."""
        status, latencia = service.check_status()
        self.storage.save_result(service, status, latencia)
        
        if service.last_status is not None and service.last_status != status:
            self.notifier.notify(service.name, status)
        
        service.last_status = status
        status_icon = "ONLINE ✅" if status else "OFFLINE ❌"
        # Padrão brasileiro D/M/Y via modulo.py
        data_verif = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        if self.tree.exists(service.name):
            tipo = self.tree.set(service.name, "tipo")
            self.tree.item(service.name, values=(tipo, status_icon, f"{latencia}ms", data_verif))

    def update_loop(self):
        """Loop infinito de monitoramento em threads."""
        for s in self.services:
            t = threading.Thread(target=self.run_check, args=(s,), daemon=True)
            t.start()
        # Agenda próxima verificação em 30 segundos
        self.root.after(30000, self.update_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = UptimeApp(root)
    root.mainloop()
