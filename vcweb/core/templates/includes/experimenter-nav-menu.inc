{% load tags %}

{% url home as home %}
{% url core:dashboard as dashboard %}
{% url core:login as login %}
{% url core:logout as logout %}
{% url core:profile as profile %}

<div id='menu'>
<ul>
	<li class='{% active_re request dashboard %}'><a href='{{ dashboard }}'>Dashboard</a></li>
        {% if "experiment" in request.path %}
        <li class='{% active_re request "experiment" %}'><a name='experiment'>Experiment</a></li>
        {% endif %}
	<li class='{% active request profile %}'><a href='{{ profile }}'>Your Account</a></li>
	<li><a href='{{ logout }}'>Logout</a></li>
</ul>
</div>
