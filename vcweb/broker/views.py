from django.shortcuts import get_object_or_404, render, redirect

def participate(request, experiment_id=None):
    participant = request.user.participant
    return render(request, 'broker/participate.html', {
        'participant': participant,

        })
