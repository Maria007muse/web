from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, validate_email
from django.contrib.auth import get_user_model
from django.forms import PasswordInput, ModelForm
from .models import Destination, Review, ActivityType, Language, Tag, Vibe, ComfortLevel

class SearchForm(forms.Form):
    country = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Страна'})
    )

    climate = forms.MultipleChoiceField(
        required=False,
        choices=Destination.CLIMATE_CHOICES,
        widget=forms.SelectMultiple(attrs={
            'class': 'selectpicker',
            'multiple': 'multiple',
            'title': 'Климат',
            'data-none-selected-text': 'Климат',
            'data-selected-text-format': 'static',
            'data-show-tick': 'true',
        })
    )

    activity_types = forms.MultipleChoiceField(  # Переименовано
        required=False,
        choices=ActivityType.ACTIVITY_CHOICES,  # Явно указаны choices
        widget=forms.SelectMultiple(attrs={
            'class': 'selectpicker',
            'multiple': 'multiple',
            'title': 'Активность',
            'data-none-selected-text': 'Активность',
            'data-selected-text-format': 'static',
            'data-show-tick': 'true',
        })
    )

    season = forms.MultipleChoiceField(
        required=False,
        choices=Destination.SEASON_CHOICES,
        widget=forms.SelectMultiple(attrs={
            'class': 'selectpicker',
            'multiple': 'multiple',
            'title': 'Сезон',
            'data-none-selected-text': 'Сезон',
            'data-selected-text-format': 'static',
            'data-show-tick': 'true',
        })
    )

    comfort_level = forms.MultipleChoiceField(
        required=False,
        choices=[],
        widget=forms.SelectMultiple(attrs={
            'class': 'selectpicker',
            'multiple': 'multiple',
            'title': 'Уровень комфорта',
            'data-none-selected-text': 'Уровень комфорта',
            'data-selected-text-format': 'static',
            'data-show-tick': 'true',
        })
    )

    vibe = forms.MultipleChoiceField(
        required=False,
        choices=[],
        widget=forms.SelectMultiple(attrs={
            'class': 'selectpicker',
            'multiple': 'multiple',
            'title': 'Атмосфера',
            'data-none-selected-text': 'Атмосфера',
            'data-selected-text-format': 'static',
            'data-show-tick': 'true',
        })
    )

    language = forms.MultipleChoiceField(
        required=False,
        choices=[],
        widget=forms.SelectMultiple(attrs={
            'class': 'selectpicker',
            'multiple': 'multiple',
            'title': 'Язык общения',
            'data-none-selected-text': 'Язык общения',
            'data-selected-text-format': 'static',
            'data-show-tick': 'true',
        })
    )

    tags = forms.MultipleChoiceField(
        required=False,
        choices=[],
        widget=forms.CheckboxSelectMultiple
    )

    family_friendly = forms.BooleanField(required=False, label='Семейный отдых')
    visa_required = forms.BooleanField(required=False, label='Нужна виза')

    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('relevance', 'По релевантности'),
            ('rating', 'По рейтингу'),
            ('popularity', 'По популярности'),
        ],
        widget=forms.Select(attrs={'class': 'selectpicker', 'title': 'Сортировка'})
    )

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

        self.fields['activity_types'].choices = [(a.name, a.name) for a in ActivityType.objects.all()]
        self.fields['language'].choices = [(l.name, l.name) for l in Language.objects.all()]
        self.fields['tags'].choices = [(t.name, t.name) for t in Tag.objects.all()]
        self.fields['vibe'].choices = [(v.name, v.name) for v in Vibe.objects.all()]
        self.fields['comfort_level'].choices = [(c.name, c.name) for c in ComfortLevel.objects.all()]

        placeholder_map = {
            'climate': 'Климат',
            'activity_types': 'Активность',
            'season': 'Сезон',
            'comfort_level': 'Уровень комфорта',
            'language': 'Язык общения',
            'vibe': 'Атмосфера',
            'tags': 'Теги',
        }

        for field_name, field in self.fields.items():
            if isinstance(field, (forms.ChoiceField, forms.MultipleChoiceField)) and field_name != 'sort_by':
                placeholder = placeholder_map.get(field_name, 'Выберите')
                field.widget.attrs.update({
                    'data-placeholder': placeholder,
                    'title': placeholder,
                    'data-none-selected-text': placeholder,
                    'data-deselect-all-text': 'Очистить',
                    'data-select-all-text': 'Выбрать все',
                    'data-show-tick': 'true',
                    'data-live-search': 'false'
                })

        if self.data:
            for field_name, field in self.fields.items():
                if isinstance(field, forms.MultipleChoiceField):
                    if field_name in self.data:
                        values = self.data.getlist(field_name)
                        self.fields[field_name].initial = values
                elif isinstance(field, forms.BooleanField):
                    self.fields[field_name].initial = field_name in self.data
                elif field_name in self.data and not isinstance(field, forms.MultipleChoiceField):
                    value = self.data.get(field_name)
                    if value:
                        self.fields[field_name].initial = value


class LoginForm(forms.Form):
    username = forms.CharField(required=True, label='Username')
    password = forms.CharField(required=True, label='Пароль')


class RegisterForm(ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['username', 'email']

    username = forms.CharField(
        min_length=3, max_length=10, required=True, label='Никнейм',
        validators=[
            RegexValidator(
                regex='^[a-zA-Z0-9]*$',
                message='Может содержать только латинские буквы и цифры',
                code='invalid_username'
            ),
        ]
    )
    email = forms.CharField(min_length=3, required=True, label='Email')
    password = forms.CharField(widget=PasswordInput(), required=True, label='Пароль')
    password_confirm = forms.CharField(widget=PasswordInput(), required=True, label='Повторите пароль')

    def clean(self):
        # Валидация формы регистрации
        cleaned_data = super(RegisterForm, self).clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password != password_confirm:
            raise forms.ValidationError(
                {'password_confirm': "Пароли не совпадают", 'password': ''}
            )

        username = self.cleaned_data.get("username")
        if get_user_model().objects.filter(username=username).exists():
            raise forms.ValidationError({'username': "Такой логин уже занят"})

        try:
            validate_email(self.cleaned_data.get("email"))
        except ValidationError:
            raise forms.ValidationError({'email': "Email не является валидным адресом"})

        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, str(i)) for i in range(1, 6)]),
            'text': forms.Textarea(attrs={'rows': 5}),
        }

    def clean_text(self):
        # Проверка длины текста отзыва
        text = self.cleaned_data.get('text')
        if len(text.strip()) < 50:
            raise forms.ValidationError("Комментарий должен содержать не менее 50 символов.")
        return text
