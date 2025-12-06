from netbox.plugins import PluginMenuButton, PluginMenuItem, PluginMenu
from netbox.choices import ButtonColorChoices


menu = PluginMenu(
    label='Meraki Sync',
    groups=(
        (
            'Meraki',
            (
                PluginMenuItem(
                    link='plugins:netbox_meraki:dashboard',
                    link_text='Dashboard',
                    buttons=()
                ),
                PluginMenuItem(
                    link='plugins:netbox_meraki:sync',
                    link_text='Sync Now',
                    buttons=(
                        PluginMenuButton(
                            link='plugins:netbox_meraki:sync',
                            title='Sync from Meraki',
                            icon_class='mdi mdi-sync',
                            color=ButtonColorChoices.BLUE
                        ),
                    )
                ),
                PluginMenuItem(
                    link='plugins:netbox_meraki:config',
                    link_text='Configuration',
                    buttons=()
                ),
            )
        ),
    ),
    icon_class='mdi mdi-cloud-sync'
)
