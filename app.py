from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
import os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'segredo123'

DB = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'agendamentos.db')

def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                email TEXT,
                data TEXT NOT NULL,
                horario TEXT NOT NULL,
                tipo TEXT NOT NULL,
                plano_saude TEXT NOT NULL,
                especialidade TEXT,
                tipo_exame TEXT
            )
        ''')

# Endereços genéricos por plano
enderecos_planos = {
    "SUS": "Unidade Básica de Saúde Central – Rua 13 de Maio, 55, Indaiatuba-SP",
    "Unimed": "Centro Médico Unimed – Av. Conceição, 1020, Indaiatuba-SP",
    "Bradesco Saúde": "Clínica Vida Bradesco – Rua Humaitá, 140, Indaiatuba-SP",
    "Amil": "Amil Saúde Center – Av. Francisco de Paula Leite, 880, Indaiatuba-SP",
    "Outro": "Policlínica Vital – Rua das Rosas, 300, Indaiatuba-SP"
}

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET'])
def login():
    usuario = request.args.get('usuario', '').strip()
    email = request.args.get('email', '').strip()
    senha = request.args.get('senha', '').strip()

    if usuario and email and senha:
        session['usuario'] = usuario
        session['email'] = email
        return redirect('/agendamento')
    else:
        flash('Preencha todos os campos do login!', 'erro')
        return render_template('login.html')

@app.route('/agendamento', methods=['GET', 'POST'])
def index():
    if 'email' not in session:
        flash('Você precisa estar logado para acessar o agendamento.', 'erro')
        return redirect('/login')

    email_usuario = session['email']

    horarios_disponiveis = ['08:00', '09:00', '10:00', '11:00', '14:00', '15:00', '16:00']
    especialidades = ['Clínico Geral', 'Pediatria', 'Cardiologia', 'Dermatologia']
    tipos_exame = ['Sangue', 'Urina', 'Raio-X', 'Ultrassom']
    planos_saude = ['SUS', 'Unimed', 'Bradesco Saúde', 'Amil', 'Outro']

    if request.method == 'POST':
        data_str = request.form.get('data', '').strip()
        tipo = request.form.get('tipo', '').strip()
        horario = request.form.get('horario', '').strip()
        plano = request.form.get('plano_saude', '').strip()
        especialidade = request.form.get('especialidade', '').strip()
        tipo_exame = request.form.get('tipo_exame', '').strip()

        if not data_str or not tipo or not horario or not plano:
            flash('Preencha todos os campos obrigatórios!', 'erro')
        else:
            try:
                data_consulta = datetime.strptime(data_str, '%Y-%m-%d').date()
                hoje = date.today()

                # ❗ Bloqueio de data anterior à hoje e superior a 2025
                if data_consulta < hoje:
                    flash('A data não pode ser anterior à data atual.', 'erro')
                elif data_consulta.year > 2025:
                    flash('A data não pode ser posterior ao ano de 2025.', 'erro')
                else:
                    with sqlite3.connect(DB) as conn:
                        cursor = conn.cursor()
                        erro_encontrado = False

                        # ❗ 1 agendamento por horário
                        cursor.execute("""
                            SELECT COUNT(*) FROM agendamentos
                            WHERE data = ? AND horario = ?
                        """, (data_str, horario))
                        if cursor.fetchone()[0] >= 1:
                            flash('Já existe um agendamento neste horário.', 'erro')
                            erro_encontrado = True

                        # ❗ 1 subtipo de consulta por dia
                        if tipo == 'Consulta':
                            cursor.execute("""
                                SELECT COUNT(*) FROM agendamentos
                                WHERE data = ? AND tipo = 'Consulta' AND especialidade = ?
                            """, (data_str, especialidade))
                            if cursor.fetchone()[0] >= 1:
                                flash('Já existe uma consulta dessa especialidade neste dia.', 'erro')
                                erro_encontrado = True

                        # ❗ 1 subtipo de exame por dia
                        elif tipo == 'Exame':
                            cursor.execute("""
                                SELECT COUNT(*) FROM agendamentos
                                WHERE data = ? AND tipo = 'Exame' AND tipo_exame = ?
                            """, (data_str, tipo_exame))
                            if cursor.fetchone()[0] >= 1:
                                flash('Já existe um exame deste tipo neste dia.', 'erro')
                                erro_encontrado = True

                        if not erro_encontrado:
                            cursor.execute("""
                                INSERT INTO agendamentos (nome, email, data, horario, tipo, plano_saude, especialidade, tipo_exame)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (session.get('usuario', ''), email_usuario, data_str, horario, tipo, plano, especialidade, tipo_exame))
                            conn.commit()

                            endereco = enderecos_planos.get(plano, "Unidade de Atendimento – Indaiatuba-SP")
                            flash(f'{tipo} agendado com sucesso! Compareça em: {endereco}', 'sucesso')
                            return redirect('/agendamento')

            except ValueError:
                flash('Formato de data inválido. Use o formato AAAA-MM-DD.', 'erro')

    return render_template('index.html',
                           horarios=horarios_disponiveis,
                           especialidades=especialidades,
                           tipos_exame=tipos_exame,
                           planos_saude=planos_saude,
                           usuario=session.get('usuario', ''),
                           email=email_usuario)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
