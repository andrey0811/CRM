from django import forms

from apps.users.models import Permission, Role, User


MODULES = [choice[0] for choice in Permission.MODULE_CHOICES]


class LoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Parol', widget=forms.PasswordInput)


class VerifyCodeForm(forms.Form):
    code = forms.CharField(
        label='Tasdiqlash kodi',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'autocomplete': 'one-time-code'}),
    )


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label='Parol',
        widget=forms.PasswordInput,
        min_length=8,
    )

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'user_type', 'role', 'is_staff']
        widgets = {
            'user_type': forms.Select,
            'role': forms.Select,
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    new_password = forms.CharField(
        label='Yangi parol',
        required=False,
        widget=forms.PasswordInput,
        min_length=8,
    )

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'user_type', 'role', 'is_staff', 'is_active']
        widgets = {
            'user_type': forms.Select,
            'role': forms.Select,
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user


class UserSearchForm(forms.Form):
    q = forms.CharField(required=False, label='Qidiruv')
    user_type = forms.ChoiceField(
        required=False,
        choices=[('', 'Barchasi')] + list(User.UserType.choices),
        label='Tur',
    )
    role = forms.ModelChoiceField(
        required=False,
        queryset=Role.objects.all(),
        empty_label='Barcha rollar',
        label='Rol',
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Barchasi'),
            ('active', 'Faol'),
            ('blocked', 'Bloklangan'),
            ('archived', 'Arxiv'),
        ],
        label='Holat',
    )


class RolePermissionsForm(forms.Form):
    def __init__(self, *args, role=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        existing = {}
        if role:
            existing = {
                perm.module: perm
                for perm in role.permissions.all()
            }

        for module, label in Permission.MODULE_CHOICES:
            perm = existing.get(module)
            self.fields[f'{module}_read'] = forms.BooleanField(
                required=False,
                label=f'{label} — o\'qish',
                initial=perm.can_read if perm else False,
            )
            self.fields[f'{module}_write'] = forms.BooleanField(
                required=False,
                label=f'{label} — yozish',
                initial=perm.can_write if perm else False,
            )
            self.fields[f'{module}_delete'] = forms.BooleanField(
                required=False,
                label=f'{label} — o\'chirish',
                initial=perm.can_delete if perm else False,
            )

    def save(self):
        if not self.role:
            return

        for module, _label in Permission.MODULE_CHOICES:
            can_read = self.cleaned_data.get(f'{module}_read', False)
            can_write = self.cleaned_data.get(f'{module}_write', False)
            can_delete = self.cleaned_data.get(f'{module}_delete', False)

            if can_read or can_write or can_delete:
                Permission.objects.update_or_create(
                    role=self.role,
                    module=module,
                    defaults={
                        'can_read': can_read,
                        'can_write': can_write,
                        'can_delete': can_delete,
                    },
                )
            else:
                Permission.objects.filter(role=self.role, module=module).delete()
