from django.conf import settings


def axes_cooloff(request):
    # Calculate the cool-off time using your progressive_cooloff function
    cooloff_time = settings.AXES_COOLOFF_TIME

    if isinstance(cooloff_time, int):
        # If it's an integer, assume it's in hours
        if cooloff_time>1:
            formatted_cooloff = f"{cooloff_time} hours"
        else:
            formatted_cooloff = f"{cooloff_time} hour"
    else:
        # If it's a float, assume it's already in seconds
        cooloff_seconds = cooloff_time * 3600  # Convert hours to seconds
        formatted_cooloff = f"{cooloff_seconds} seconds"

    return {'axes_cooloff_time': formatted_cooloff}
