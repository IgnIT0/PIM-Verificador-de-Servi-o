import tkinter as tk
from tkinter import messagebox, ttk
import threading
import datetime
from modulo import Service, Notifier, Storage

class UptimeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor de Infraestrutura - PIM ADS")
        self.root.geometry("900x650")
        
        # --- DEFINIÇÃO DE CORES (DARK MODE) ---
        self.colors = {
            "bg": "#1e1e1e",
            "card": "#2d2d2d",
            "fg": "#ffffff",
            "accent": "#007acc",
            "success": "#4ec9b0",
            "danger": "#f44747",
            "border": "#3e3e3e"
        }

        self.root.configure(bg=self.colors["bg"])
        
        self.notifier = Notifier()
        self.storage = Storage()
        self.services = []

        # Estilização do Treeview (Tabela) para o Modo Escuro
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Treeview", 
            background=self.colors["card"], 
            foreground=self.colors["fg"], 
            fieldbackground=self.colors["card"],
            bordercolor=self.colors["border"],
            rowheight=30
        )
        self.style.map("Treeview", background=[('selected', self.colors["accent"])])
        self.style.configure("Treeview.Heading", background=self.colors["border"], foreground=self.colors["fg"], borderwidth=0)

        # --- ÁREA DE CADASTRO ---
        frame_add = tk.LabelFrame(root, text=" Adicionar Alvo de Monitoramento ", 
                                  bg=self.colors["bg"], fg=self.colors["fg"], padx=15, pady=15)
        frame_add.pack(fill="x", padx=20, pady=10)

        # Nome
        tk.Label(frame_add, text="Nome:", bg=self.colors["bg"], fg=self.colors["fg"]).grid(row=0, column=0, padx=5)
        self.ent_name = tk.Entry(frame_add, width=15, bg=self.colors["card"], fg=self.colors["fg"], insertbackground="white")
        self.ent_name.grid(row=0, column=1, padx=5)

        # Alvo (IP ou URL)
        tk.Label(frame_add, text="Alvo (IP/URL):", bg=self.colors["bg"], fg=self.colors["fg"]).grid(row=0, column=2, padx=5)
        self.ent_target = tk.Entry(frame_add, width=25, bg=self.colors["card"], fg=self.colors["fg"], insertbackground="white")
        self.ent_target.grid(row=0, column=3, padx=5)

        # Protocolo (Seletor)
        tk.Label(frame_add, text="Protocolo:", bg=self.colors["bg"], fg=self.colors["fg"]).grid(row=0, column=4, padx=5)
        self.combo_proto = ttk.Combobox(frame_add, values=["HTTP", "ICMP"], width=8, state="readonly")
        self.combo_proto.current(0)
        self.combo_proto.grid(row=0, column=5, padx=5)

        # Botões
        self.btn_add = tk.Button(frame_add, text="ADICIONAR", command=self.add_service, 
                                 bg=self.colors["accent"], fg="white", font=("Arial", 9, "bold"), padx=10)
        self.btn_add.grid(row=0, column=6, padx=5)

        self.btn_remove = tk.Button(frame_add, text="REMOVER", command=self.remove_service, 
                                    bg=self.colors["danger"], fg="white", font=("Arial", 9, "bold"), padx=10)
        self.btn_remove.grid(row=0, column=7, padx=5)

        # --- TABELA DE MONITORAMENTO ---
        colunas = ("nome", "tipo", "status", "latencia", "visto")
        self.tree = ttk.Treeview(root, columns=colunas, show="headings")
        
        self.tree.heading("nome", text="SERVIÇO / SERVIDOR")
        self.tree.heading("tipo", text="IP / VERSÃO")
        self.tree.heading("status", text="STATUS")
        self.tree.heading("latencia", text="LATÊNCIA")
        self.tree.heading("visto", text="ÚLTIMA ATUALIZAÇÃO")

        self.tree.column("nome", width=200)
        self.tree.column("tipo", width=120, anchor="center")
        self.tree.column("status", width=120, anchor="center")
        self.tree.column("latencia", width=100, anchor="center")
        self.tree.column("visto", width=180, anchor="center")
        
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

        self.load_saved_data()
        self.update_loop()

    def add_service(self):
        name = self.ent_name.get().strip()
        target = self.ent_target.get().strip()
        protocol = self.combo_proto.get()

        if not name or not target:
            messagebox.showwarning("Erro", "Preencha todos os campos corretamente.")
            return

        novo_servico = Service(name, target, protocol)
        self.services.append(novo_servico)
        
        # Insere na tabela com a versão do IP detectada no módulo
        self.tree.insert("", "end", iid=name, values=(name, novo_servico.ip_version, "⏳ Aguardando", "--", "--"))
        
        self.storage.save_services_config(self.services)
        self.ent_name.delete(0, tk.END)
        self.ent_target.delete(0, tk.END)

    def remove_service(self):
        selected = self.tree.selection()
        if not selected: return
        
        service_name = selected[0]
        self.services = [s for s in self.services if s.name != service_name]
        self.tree.delete(service_name)
        self.storage.save_services_config(self.services)

    def load_saved_data(self):
        saved_list = self.storage.load_services_config()
        for item in saved_list:
            # Reconstrói o serviço com o protocolo salvo
            novo = Service(item['name'], item['target'], item.get('protocol', 'HTTP'))
            self.services.append(novo)
            self.tree.insert("", "end", iid=novo.name, values=(novo.name, novo.ip_version, "⏳ Carregando", "--", "--"))

    def run_check(self, service):
        status_atual, latencia = service.check_status()
        self.storage.save_result(service, status_atual, latencia) # Envia objeto completo para o CSV

        if service.last_status is not None and service.last_status != status_atual:
            self.notifier.notify(service.name, status_atual)
        
        service.last_status = status_atual
        status_texto = "ONLINE ✅" if status_atual else "OFFLINE ❌"
        # Data formatada no padrão brasileiro D/M/Y
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        if self.tree.exists(service.name):
            self.tree.item(service.name, values=(service.name, service.ip_version, status_texto, f"{latencia}ms", agora))

    def update_loop(self):
        for s in self.services:
            t = threading.Thread(target=self.run_check, args=(s,))
            t.daemon = True
            t.start()
        # Intervalo de 30 segundos
        self.root.after(30000, self.update_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = UptimeApp(root)
    root.mainloop()
