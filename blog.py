from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from forms import RegisterForm, LoginForm, ArticleForm

#Session başlatmak için gerekli secret_key
app = Flask(__name__)
app.secret_key = "blog"

#SQL Bağlantıları
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)

#Giriş gerektiren sayfalar için decorater
def login_required(page):
    @wraps(page)
    def decorated_function(*args, **kwargs):
        if("logged_in" in session):
            return page(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın.","danger")
            return redirect(url_for("login"))
    return decorated_function

#Anasayfa
@app.route("/")
def index():
    return render_template("index.html")

#Hakkımda
@app.route("/about")
def about():
    return render_template("about.html")

#Makaleler
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    query = "select * from articles"
    result = cursor.execute(query)
    if(result > 0):
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

#Kayıt olma
@app.route("/register", methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        query = "insert into users(name, email, username, password) values(%s, %s, %s, %s)"
        cursor.execute(query, (name, email, username, password))
        mysql.connection.commit()
        cursor.close()
        flash("Kaydınız başarılı!","success")
        return redirect(url_for("login"))
    else:
        return render_template("/register.html", form = form)

#Giriş yap
@app.route("/login", methods = ['GET','POST'])
def login():   
    form = LoginForm(request.form)

    if(request.method == "POST"):  
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        query = "select * from users where username = %s"
        result = cursor.execute(query, (username, ))
        if(result > 0):
            data = cursor.fetchone()
            real_password = data["password"]
            if(sha256_crypt.verify(password_entered, real_password)):
                flash("Başarıyla giriş yaptınız!","success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Girdiğiniz şifre yanlış, lütfen kontrol edin ve tekrar deneyin","danger")
                redirect(url_for("login"))
        else:
            flash("Kullanıcı adı yanlış veya böyle bir kullanıcı yok","danger")
            return redirect(url_for("login"))
    return render_template("login.html", form = form)

#Çıkış yap
@app.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla çıkış yaptınız!\nGörüşmek üzere!", "success")
    return redirect(url_for("index"))

#Kontrol paneli, giriş gerektiren decorater ile
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    query = "select * from articles where author = %s"
    result = cursor.execute(query, (session["username"], ))
    if (result > 0):
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")

#Makaleyi görüntüleyen sayfa
@app.route("/article/<string:id>")
def article(id):
        cursor = mysql.connection.cursor()
        query = "select * from articles where id = %s"
        result = cursor.execute(query, (id, ))
        if (result > 0):
            article = cursor.fetchone()
            return render_template("article.html", article = article)
        else:
            return render_template("article.html")

#Makale ekleme
@app.route("/addarticle", methods = ["GET","POST"])
@login_required
def add_article():
    form = ArticleForm(request.form)
    if (request.method == "POST" and form.validate()):
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        query = "insert into articles(title, author, content) values(%s, %s, %s)"
        cursor.execute(query, (title, session["username"], content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla eklendi","success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html", form = form)

#Makale silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    query = "select * from articles where author = %s and id = %s"
    result = cursor.execute(query, (session["username"], id))
    if(result > 0):
        query = "delete from articles where id = %s"
        cursor.execute(query, (id, ))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla silindi","success")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya silmeye yetkiniz yok","danger")
        return redirect(url_for("dashboard"))

#Makale güncelleme
@app.route("/edit/<string:id>", methods = ["GET","POST"])
@login_required
def edit(id):
    if(request.method == "GET"):
        cursor = mysql.connection.cursor()
        query = "select * from articles where author = %s and id = %s"
        result = cursor.execute(query, (session["username"], id))
        if(result > 0):
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("/edit.html", form = form)
        else:
            flash("Böyle bir makale yok veya silmeye yetkiniz yok","danger")
        return redirect(url_for("dashboard"))
    else:
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        
        query = "update articles set title = %s, content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(query, (newTitle, newContent, id))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla düzenlendi","success")
        return redirect(url_for("dashboard"))

#Arama
@app.route("/search", methods=["GET","POST"])
def search():
    if(request.method == "GET"):
        return redirect(url_for("articles"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()
        query = f"select * from articles where title like '%{keyword}%'"
        result = cursor.execute(query)

        if(result == 0):
            flash("Aranan kelimeye uygun makale bulunamadı", "alert")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles = articles)
        

#Flask quickstart'tan gelen kod
if __name__ == "__main__":
    
    app.run(debug = True)