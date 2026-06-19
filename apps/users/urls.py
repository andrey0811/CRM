from django.urls import path

from apps.users import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('verify-code/', views.verify_code_view, name='verify-code'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('demo/clients/', views.clients_demo_view, name='demo-clients'),
    path('admin-panel/users/', views.admin_user_list, name='admin-user-list'),
    path('admin-panel/users/create/', views.admin_user_create, name='admin-user-create'),
    path('admin-panel/users/<int:user_id>/edit/', views.admin_user_edit, name='admin-user-edit'),
    path('admin-panel/users/<int:user_id>/archive/', views.admin_user_archive, name='admin-user-archive'),
    path('admin-panel/users/<int:user_id>/block/', views.admin_user_block, name='admin-user-block'),
    path('admin-panel/users/<int:user_id>/unblock/', views.admin_user_unblock, name='admin-user-unblock'),
    path('admin-panel/users/<int:user_id>/force-logout/', views.admin_force_logout, name='admin-force-logout'),
    path('admin-panel/roles/', views.admin_role_list, name='admin-role-list'),
    path('admin-panel/roles/<int:role_id>/', views.admin_role_edit, name='admin-role-edit'),
]
