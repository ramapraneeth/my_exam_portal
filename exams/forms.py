from django import forms


class CandidateLoginForm(forms.Form):
    candidate_id = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'placeholder': '11111',
            'class': 'login-input',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': '*****',
            'class': 'login-input',
        })
    )
