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
                especialidade TEXT,
                tipo_exame TEXT
            )
        ''')

@app.route('/')
def landing():
    return render_template('landing.html')  # Página inicial = landing

@app.route('/login', methods=['GET'])
def login():
    usuario = request.args.get('usuario', '').strip()
    email = request.args.get('email', '').strip()
    senha = request.args.get('senha', '').strip()

    if usuario and email and senha:
        session['usuario'] = usuario
        session['email'] = email
        return redirect('/postos')
    else:
        flash('Preencha todos os campos do login!', 'erro')
        return render_template('landing.html')

@app.route('/postos')
def postos():
    return render_template('postos.html')

@app.route('/agendamento', methods=['GET', 'POST'])
def index():
    if 'email' not in session:
        flash('Você precisa estar logado para acessar o agendamento.', 'erro')
        return redirect('/login')

    email_usuario = session['email']
    horarios_disponiveis = ['08:00', '09:00', '10:00', '11:00', '14:00', '15:00', '16:00']
    especialidades = ['Clínico Geral', 'Pediatria', 'Cardiologia', 'Dermatologia']
    tipos_exame = ['Sangue', 'Urina', 'Raio-X', 'Ultrassom']

    if request.method == 'POST':
        data_str = request.form.get('data', '').strip()
        tipo = request.form.get('tipo', '').strip()
        horario = request.form.get('horario', '').strip()
        especialidade = request.form.get('especialidade', '').strip()
        tipo_exame = request.form.get('tipo_exame', '').strip()

        if not data_str or not tipo or not horario:
            flash('Preencha todos os campos obrigatórios!', 'erro')
        else:
            try:
                data_consulta = datetime.strptime(data_str, '%Y-%m-%d').date()
                hoje = date.today()

                if data_consulta < hoje:
                    flash('A data não pode ser anterior à data atual.', 'erro')
                elif data_consulta.year > 2025:
                    flash('A data não pode ser superior a 2025.', 'erro')
                else:
                    with sqlite3.connect(DB) as conn:
                        cursor = conn.cursor()
                        erro = False

                        # Impede múltiplos agendamentos no mesmo horário para o mesmo usuário
                        cursor.execute("""
                            SELECT COUNT(*) FROM agendamentos
                            WHERE data = ? AND horario = ? AND email = ?
                        """, (data_str, horario, email_usuario))
                        if cursor.fetchone()[0] > 0:
                            flash('Você já possui um agendamento neste horário.', 'erro')
                            erro = True

                        # Vacina - 1 por dia por email + limite de 5 no horário
                        if tipo == 'Vacina':
                            cursor.execute("""
                                SELECT COUNT(*) FROM agendamentos
                                WHERE email = ? AND data = ? AND tipo = 'Vacina'
                            """, (email_usuario, data_str))
                            if cursor.fetchone()[0] > 0:
                                flash('Você já agendou uma vacinação neste dia.', 'erro')
                                erro = True
                            else:
                                cursor.execute("""
                                    SELECT COUNT(*) FROM agendamentos
                                    WHERE data = ? AND horario = ? AND tipo = 'Vacina'
                                """, (data_str, horario))
                                if cursor.fetchone()[0] >= 5:
                                    flash('Limite de vacinações neste horário atingido.', 'erro')
                                    erro = True

                        # Consulta - apenas 1 por subtipo por horário
                        elif tipo == 'Consulta':
                            cursor.execute("""
                                SELECT COUNT(*) FROM agendamentos
                                WHERE data = ? AND horario = ? AND tipo = 'Consulta' AND especialidade = ?
                            """, (data_str, horario, especialidade))
                            if cursor.fetchone()[0] > 0:
                                flash('Já existe uma consulta dessa especialidade neste horário.', 'erro')
                                erro = True

                        # Exame - 1 por subtipo por dia por email + até 5 no mesmo horário
                        elif tipo == 'Exame':
                            cursor.execute("""
                                SELECT COUNT(*) FROM agendamentos
                                WHERE email = ? AND data = ? AND tipo = 'Exame' AND tipo_exame = ?
                            """, (email_usuario, data_str, tipo_exame))
                            if cursor.fetchone()[0] > 0:
                                flash('Você já agendou esse tipo de exame neste dia.', 'erro')
                                erro = True
                            else:
                                cursor.execute("""
                                    SELECT COUNT(*) FROM agendamentos
                                    WHERE data = ? AND horario = ? AND tipo = 'Exame' AND tipo_exame = ?
                                """, (data_str, horario, tipo_exame))
                                if cursor.fetchone()[0] >= 5:
                                    flash('Limite de agendamentos deste exame neste horário atingido.', 'erro')
                                    erro = True

                        if not erro:
                            cursor.execute("""
                                INSERT INTO agendamentos
                                (nome, email, data, horario, tipo, especialidade, tipo_exame)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                session.get('usuario', ''),
                                email_usuario,
                                data_str,
                                horario,
                                tipo,
                                especialidade if tipo == 'Consulta' else '',
                                tipo_exame if tipo == 'Exame' else ''
                            ))
                            conn.commit()

                            flash(f'{tipo} agendado com sucesso! Comparecer na Unidade de Saúde de Indaiatuba.', 'sucesso')
                            return redirect('/agendamento')

            except ValueError:
                flash('Formato de data inválido. Use AAAA-MM-DD.', 'erro')

    return render_template('index.html',
                           horarios=horarios_disponiveis,
                           especialidades=especialidades,
                           tipos_exame=tipos_exame,
                           usuario=session.get('usuario', ''),
                           email=email_usuario)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
