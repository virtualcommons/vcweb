{% load tags %}

{% url home as home %}
{% url core:dashboard as dashboard %}
{% url core:login as login %}
{% url core:logout as logout %}
{% url core:profile as profile %}

<div id='menu'>
<ul>
	<li class='{% active request dashboard %}'><a href='{{ dashboard }}'>Dashboard</a></li>
        {% if "participate" in request.path %}
        <li class='{% active_re request "participate$" %}'><a href='{{ current }}'>Participate</a></li>
        {% else %}
	<li class='{% active request profile %}'><a href='{{ profile }}'>Profile</a></li>
        {% endif %}
	<li><a href='{{ logout }}'>Logout</a></li>
</ul>
</div>
