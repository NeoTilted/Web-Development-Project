from wtforms import Form, StringField, PasswordField, RadioField, SelectField, TextAreaField, validators

class UserLoginIn(Form):
    username = StringField('Username: ', [validators.Length(min=1,max=100),validators.DataRequired()])
    password = PasswordField('Password: ',[validators.Length(min=1,max=100),validators.DataRequired()])