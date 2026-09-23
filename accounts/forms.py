from django import forms


class NameSignupForm(forms.Form):
    """allauth'un ACCOUNT_SIGNUP_FORM_CLASS kancasına eklenen 'ad' alanı."""

    first_name = forms.CharField(
        label="Ad",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Adın", "autocomplete": "given-name"}),
    )

    field_order = ["first_name"]

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.save(update_fields=["first_name"])
