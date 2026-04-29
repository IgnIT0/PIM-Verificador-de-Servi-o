import tkinter as tk
from tkinter import messagebox, ttk
import threading
import datetime
from modulo import Service, Notifier, Storage

class UptimeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor de Uptime Profissional - PIM")
        self.root.geometry("800x600")
        
        self.notifier = Notifier()
        self.storage = Storage()
        self.services = []

        # --- CABEÇALHO E CADASTRO ---
        frame_add = tk.LabelFrame(root, text=" Configuração de Monitoramento ", padx=15, pady=15)
        frame_add.pack(fill="x", padx=20, pady=10)

        tk.Label(frame_add, text="Nome:").grid(row=0, column=0)
        self.ent_name = tk.Entry(frame_add, width=15)
        self.ent_name.grid(row=0, column=1, padx=5)

        tk.Label(frame_add, text="URL:").grid(row=0, column=2)
        self.ent_url = tk.Entry(frame_add, width=30)
        self.ent_url.insert(0, "https://")
        self.ent_url.grid(row=0, column=3, padx=5)

        self.btn_add = tk.Button(frame_add, text="Adicionar", command=self.add_service, bg="#28a745", fg="white", font=("Arial", 9, "bold"))
        self.btn_add.grid(row=0, column=4, padx=5)

        # Botão Remover (Vermelho)
        self.btn_remove = tk.Button(frame_add, text="Remover Selecionado", command=self.remove_service, bg="#dc3545", fg="white", font=("Arial", 9, "bold"))
        self.btn_remove.grid(row=0, column=5, padx=5)

        # --- TABELA DE EXIBIÇÃO ---
        colunas = ("nome", "status", "latencia", "visto")
        self.tree = ttk.Treeview(root, columns=colunas, show="headings")
        self.tree.heading("nome", text="SERVIÇO")
        self.tree.heading("status", text="STATUS")
        self.tree.heading("latencia", text="LATÊNCIA")
        self.tree.heading("visto", text="ÚLTIMA VERIFICAÇÃO")
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

        # --- CARREGAR DADOS SALVOS ---
        self.load_saved_data()

        # Iniciar loop
        self.update_loop()

    def load_saved_data(self):
        """Carrega os serviços do arquivo JSON para a memória e para a tela."""
        saved_list = self.storage.load_services_config()
        for item in saved_list:
            novo_servico = Service(item['name'], item['url'])
            self.services.append(novo_servico)
            self.tree.insert("", "end", iid=item['name'], values=(item['name'], "Carregando...", "--", "--"))

    def add_service(self):
        name = self.ent_name.get().strip()
        url = self.ent_url.get().strip()

        if not name or len(url) < 10:
            messagebox.showwarning("Aviso", "Dados inválidos.")
            return

        novo_servico = Service(name, url)
        self.services.append(novo_servico)
        self.tree.insert("", "end", iid=name, values=(name, "Aguardando...", "--", "--"))
        
        # Salva a nova lista no arquivo
        self.storage.save_services_config(self.services)
        
        self.ent_name.delete(0, tk.END)
        self.ent_url.delete(0, tk.END)

    def remove_service(self):
        """Remove o serviço selecionado da tabela, da lista e do arquivo JSON."""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Aviso", "Selecione um serviço na tabela para remover.")
            return
        
        service_name = selected_item[0]
        
        # 1. Remover da lista de objetos
        self.services = [s for s in self.services if s.name != service_name]
        
        # 2. Remover da tabela visual
        self.tree.delete(service_name)
        
        # 3. Atualizar arquivo de configuração
        self.storage.save_services_config(self.services)
        messagebox.showinfo("Sucesso", f"Serviço '{service_name}' removido.")

    def run_check(self, service):
        status_atual, latencia = service.check_status()
        self.storage.save_result(service.name, status_atual, latencia)
        
        if service.last_status is not None and service.last_status != status_atual:
            self.notifier.notify(service.name, status_atual)
        
        service.last_status = status_atual
        status_texto = "ONLINE ✅" if status_atual else "OFFLINE ❌"
        agora = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Verifica se o item ainda existe antes de atualizar (evita erro ao remover)
        if self.tree.exists(service.name):
            self.tree.item(service.name, values=(service.name, status_texto, f"{latencia}ms", agora))

    def update_loop(self):
        for s in self.services:
            t = threading.Thread(target=self.run_check, args=(s,))
            t.daemon = True
            t.start()
        self.root.after(30000, self.update_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = UptimeApp(root)
    root.mainloop()