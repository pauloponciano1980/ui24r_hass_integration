
ui24rIpAddress = data.get("UI24R_IP_ADDRESS")
entidade = data.get("entidade")

logger.error(f"Hello {ui24rIpAddress}")

if hass.states.get(entidade).state == "on":
    hass.services.call('switch', 'turn_off', {'entity_id':entidade}')
    logger.error("desliguei o switch")
else:
    hass.services.call('switch', 'turn_on', {'entity_id':entidade}')
    logger.error("desliguei o switch")
