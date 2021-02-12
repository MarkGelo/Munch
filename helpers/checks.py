from discord.ext import commands

def is_admin():
    return commands.check_any(
        commands.is_owner(), commands.has_permissions(administrator=True)
    )

def is_admin_owner_manage_channels():
    return commands.check_any(
        commands.is_owner(), commands.has_permissions(administrator=True),
        commands.has_permissions(manage_channels = True)
    )
