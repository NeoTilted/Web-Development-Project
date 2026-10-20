from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, SubmitField
from wtforms import validators
from wtforms.validators import DataRequired, EqualTo, Length, Regexp

class ForgotPasswordForm(FlaskForm):
    email = EmailField('Email Address', [
        validators.DataRequired(message="Email is required."),
        validators.Email(message="Enter a valid email address."),
        validators.Length(max=100)
    ])
    submit = SubmitField('Send Reset Link')
    
class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', [DataRequired(), Length(min=8, max=100)])
    confirm_password = PasswordField('Confirm Password', [DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')