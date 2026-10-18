from django.urls import path

from .views import set_currency, set_language, toggle_language


urlpatterns = [
    path("currency/set/<str:currency_code>/", set_currency, name="set_currency"),
    path("language/toggle/", toggle_language, name="toggle_language"),
    path("language/set/<str:language_code>/", set_language, name="set_language"),
]
