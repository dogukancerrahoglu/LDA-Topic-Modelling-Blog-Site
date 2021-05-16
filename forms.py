from wtforms import Form, StringField, TextAreaField, PasswordField, validators

#Kullanıcı kayıt formu
class RegisterForm(Form):
    name = StringField("Tam ad", validators = [validators.Length(min = 4, max = 30), validators.DataRequired(message = "Lütfen isminizi giriniz")])
    username = StringField("Kullanıcı adı", validators = [validators.Length(min = 4, max = 30)])
    email = StringField("E-posta adresi", validators = [validators.Email(message="Lütfen geçerli bir e-posta adresi girin")])
    password = PasswordField("Şifre", validators = [
        validators.DataRequired(message = "Lütfen bir şifre belirleyin"),
        validators.EqualTo(fieldname = "confirm", message = "Lütfen aynı şifreyi girdiğinizden emin olun")
    ])
    confirm = PasswordField("Şifreyi doğrula")

#Login formu
class LoginForm(Form):
    username = StringField("Kullanıcı adı")
    password = PasswordField("Şifre")

#Makale formu
class ArticleForm(Form):
    title = StringField("Makale başlığı", validators = [validators.length(min = 5, max = 100)])
    content = TextAreaField("Makale içeriği", validators = [validators.length(min = 10)])
