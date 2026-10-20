from wtforms import Form, StringField, PasswordField, EmailField, RadioField, SelectField, TextAreaField, validators
from wtforms.validators import DataRequired, EqualTo, Length, Regexp

class createAccount(Form):
    username = StringField('Username: ', [
        validators.DataRequired(),
        validators.Length(min=5, max=100)
    ])

    password = PasswordField('Password: ', [
        validators.DataRequired(),
        validators.Length(min=8, max=100),
        validators.Regexp(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$'
        )
    ])
    user_type = SelectField('User Type: ', [validators.DataRequired()], choices=[('', 'Select'), ('Senior', 'Senior'), ('Youth', 'Youth')], default='')
    email = EmailField('Email Address', [validators.DataRequired(message="Email is required."),validators.Email(message="Enter a valid email address."),validators.Length(max=100)])
    
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message="Passwords must match.")
    ])
    

