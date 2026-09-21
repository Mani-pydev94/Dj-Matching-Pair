from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path
from django.views.decorators.http import require_POST

from .models import Community


@login_required
def communities_home(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    communities = Community.objects.annotate(member_count=Count('members'))
    if query:
        communities = communities.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query)
        )
    if category and category != 'All':
        communities = communities.filter(category__iexact=category)
    return render(request, 'communities/home.html', {
        'communities': communities,
        'all_communities': Community.objects.annotate(member_count=Count('members')),
        'categories': Community.objects.exclude(category='').values_list(
            'category', flat=True
        ).distinct().order_by('category'),
        'query': query,
        'selected_category': category or 'All',
        'joined_communities': request.user.communities.annotate(member_count=Count('members')),
        'can_create': request.user.is_superuser or request.user.has_perm('communities.add_community'),
    })


@login_required
def community_detail(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    return render(request, 'communities/detail.html', {'community': community})


@login_required
@require_POST
def toggle_membership(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    if community.members.filter(id=request.user.id).exists():
        community.members.remove(request.user)
        messages.success(request, f'You left {community.name}.')
    else:
        community.members.add(request.user)
        messages.success(request, f'You joined {community.name}.')
    return HttpResponseRedirect(request.POST.get('next') or '/communities/')


urlpatterns = [
    path('', communities_home, name='communities_home'),
    path('<int:community_id>/', community_detail, name='community_detail'),
    path('<int:community_id>/membership/', toggle_membership, name='toggle_membership'),
]
