from django.urls import path
from . import views

urlpatterns = [
    path('sessions/',                                  views.session_list),
    path('sessions/create/',                           views.create_session),
    path('sessions/<int:session_id>/messages/',        views.send_message),
    path('sessions/<int:session_id>/tea/',             views.recommend_tea),
    path('sessions/<int:session_id>/bgm/',             views.recommend_bgm),
    path('sessions/<int:session_id>/questions/',       views.suggest_questions),
    path('sessions/<int:session_id>/council/',         views.inner_council),
]
