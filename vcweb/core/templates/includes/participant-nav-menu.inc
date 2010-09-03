{% load tags %}

{% url home as home %}
{% url core:participant-index as games %}
{% url core:login as login %}
{% url core:logout as logout %}
{% url core:profile as profile %}

<div id='menu'>
<ul>
	<li class='{% active request games %}'><a href='{{ games }}'>Dashboard</a></li>
	<li class='{% active request profile %}'><a href='{{ profile }}'>Account</a>
	<li><a href='{{ logout }}'>Logout</a></li>
</ul>
</div>