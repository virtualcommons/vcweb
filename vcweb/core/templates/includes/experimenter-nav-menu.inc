{% load tags %}

{% url home as home %}
{% url core:experimenter-index as experiments %}
{% url core:login as login %}
{% url core:logout as logout %}
{% url core:profile as profile %}

<div id='menu'>
<ul>
	<li class='{% active request profile %}'><a href='{{ profile }}'>Your account</a>
	<li class='{% active request experiments %}'><a href='{{ experiments }}'>Your experiments</a></li>
	<li><a href='{{ logout }}'>Logout</a></li>
</ul>
</div>