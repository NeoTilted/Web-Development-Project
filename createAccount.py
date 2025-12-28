from wtforms import Form, StringField, PasswordField, RadioField, SelectField, TextAreaField, validators

class createAccount(Form):
    username = StringField('Username: ', [validators.Length(min=1,max=100),validators.DataRequired()])
    password = PasswordField('Password: ',[validators.Length(min=1,max=100),validators.DataRequired()])
    user_type = SelectField('User Type: ', [validators.DataRequired()], choices=[('', 'Select'), ('S', 'Senior'), ('Y', 'Youth')], default='')