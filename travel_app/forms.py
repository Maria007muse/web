# forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Destination as DestinationModel  # Изменение имени модели
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.forms import PasswordInput, ModelForm
from django.core.validators import validate_email

class SearchForm(forms.ModelForm):
    class Meta:
        model = DestinationModel  # Использование измененного имени
        fields = ['climate', 'activity_type', 'budget', 'popularity', 'cultural_diversity']

    climate = forms.ChoiceField(
        choices=DestinationModel.CLIMATE_CHOICES,
        widget=forms.Select(attrs={'class': 'selectpicker', 'placeholder': 'Климат'})
    )

    activity_type = forms.ChoiceField(
        choices=DestinationModel.ACTIVITY_CHOICES,
        widget=forms.Select(attrs={'class': 'selectpicker', 'placeholder': 'Тип отдыха'})
    )

    budget = forms.ChoiceField(
        choices=DestinationModel.BUDGET_CHOICES,
        widget=forms.Select(attrs={'class': 'selectpicker', 'placeholder': 'Бюджет'})
    )

    popularity = forms.ChoiceField(
        choices=DestinationModel.POPULARITY_CHOICES,
        widget=forms.Select(attrs={'class': 'selectpicker', 'placeholder': 'Популярность'})
    )

    cultural_diversity = forms.ChoiceField(
        choices=DestinationModel.DIVERSITY_CHOICES,
        widget=forms.Select(attrs={'class': 'selectpicker', 'placeholder': 'Культурное разнообразие'})
    )

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'id':
                field.choices = [(str(key), value) for key, value in field.choices]


# форма авторизации
class LoginForm(forms.Form):
    username = forms.CharField(required=True, label='Username')
    password = forms.CharField(required=True, label='Пароль')

# форма регистрации
class RegisterForm(ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['username', 'email']

    username = forms.CharField(min_length=3, max_length=10, required=True, label='Никнейм', validators=[
        RegexValidator(
            regex='^[a-zA-Z0-9]*$',
            message='Может содержать только латинские буквы и цифры',
            code='invalid_username'
        ),
    ])

    email = forms.CharField(min_length=3, required=True, label='Email')

    password = forms.CharField(widget=PasswordInput(), required=True, label='Пароль')
    password_confirm = forms.CharField(widget=PasswordInput(), required=True, label='Повторите пароль')

    def clean(self):
        cleaned_data = super(RegisterForm, self).clean()
        # валидация паролей
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password != password_confirm:
            raise forms.ValidationError(
                {'password_confirm': "Пароли не совпадают", 'password': ''}
            )
        # валидация никнейма
        username = self.cleaned_data.get("username")

        if get_user_model().objects.filter(username=username).exists():
            raise forms.ValidationError({'username': "Такой логин уже занят"})

        # валидация email
        try:
            validate_email(self.cleaned_data.get("email"))
        except ValidationError as e:
            raise forms.ValidationError({'email': "Email не является валидным адресом"})

        return cleaned_data


