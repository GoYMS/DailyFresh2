import re
from django import forms
from captcha.fields import CaptchaField


class RegisterForm(forms.Form):
    """注册"""
    user_name = forms.CharField(label='用户名')
    pwd = forms.CharField(label='密码')
    cpwd = forms.CharField(label='再次密码')
    email = forms.EmailField()
    captcha = CaptchaField(label='验证码', )

    # 验证用户名
    def clean_user_name(self):
        # 获取传过来的数据
        user_name = self.cleaned_data.get('user_name')
        if len(user_name) < 5:
            raise forms.ValidationError(message='用户名不能小于5位')
        if len(user_name) > 20:
            raise forms.ValidationError('用户名不能大于20位')
        return user_name

    # 验证密码
    def clean_pwd(self):
        pwd = self.cleaned_data.get('pwd')
        if len(pwd) < 8:
            raise forms.ValidationError('用户名不能小于8位')
        if len(pwd) > 20:
            raise forms.ValidationError('用户名不能大于20位')
        return pwd

    # 验证邮箱
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not re.match(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', email):
            raise forms.ValidationError('邮箱格式不正确')
        return email


class LoginFrom(forms.Form):
    username = forms.CharField(max_length=20, min_length=5, error_messages={
        'max_length': '用户名不能超过20位',
        'min_length': '用户名不能少于5位',
        'require': '用户名不能为空',
    })
    pwd = forms.CharField(max_length=20, min_length=8, error_messages={
        'max_length': '密码不能超过20位',
        'min_length': '密码不能少于8位',
        'require': '密码不能为空',
    })







