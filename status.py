import discord
from discord.ext import commands
import requests, asyncio, json
from datetime import datetime

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

class myBot(commands.Bot):
    async def on_ready(self):
        await self.wait_until_ready()
        print(f'Logget inn som {self.user}!')

        self.loop.create_task(update_embed())
        
        try:
            synced = await self.tree.sync()
            print(f'Synkroniserte {len(synced)} Kommando(er)')
        except Exception as e:
            print('e: {}'.format(e))

bot = myBot(intents = intents, command_prefix = '!')

with open('config.json') as f:
    config = json.load(f)

TOKEN = config['token']
CHANNEL_ID = config['channel_id']
CHANNEL_NAME = config['channel_name']
EDIT_CHANNEL = config['edit_channel_name']
REFRESH_INTERVAL = config['refresh_interval']

async def fetch_status():
    status_response = requests.get('https://status.cfx.re/api/v2/status.json')
    components_response = requests.get('https://status.cfx.re/api/v2/components.json')
    #metrics_response = requests.get('https://status.cfx.re/metrics-display/1hck2mqcgq3h/day.json')

    status_data = status_response.json()
    components_data = components_response.json()['components']
    #metrics_data = metrics_response.json()

    #return status_data, components_data, metrics_data
    return status_data, components_data

async def update_embed():
    downtime_start, downtime_end, last_message_id = None, None, None
    embed_color, emoji = 6205745, '🟢'

    while not bot.is_closed():
        try:
            #status_data, components_data, metrics_data = await fetch_status()
            status_data, components_data = await fetch_status()
            channel = bot.get_channel(CHANNEL_ID)

            status_indicator = status_data.get('status', {}).get('indicator')

            if status_indicator == 'none':
                status_text = 'Alle Systemer I Drift'
                status_emoji = ':green_circle:'
                embed_color, emoji = 6205745, '🟢'
                if downtime_start and downtime_end:
                    downtime_duration = (downtime_end - downtime_start).total_seconds() // 60
                    mention_message = f"@here CFX er tilbake i drift etter {downtime_duration} minutter med nedetid. Alle systemer er tilbake i drift."
                    downtime_start = None
                    downtime_end = None
                    await channel.send(mention_message)
            else:
                status_text = 'Opplever Problemer'
                status_emoji = ':orange_circle:'
                embed_color, emoji = 16711680, '🔴'
                if not downtime_start:
                    downtime_start = datetime.now()
                    mention_message = f"@here CFX opplever for tiden problemer og vil ikke være tilgjengelig for alle. Vennligst vær tålmodig."
                    await channel.send(mention_message)

            embed = discord.Embed(title="🐌 CFX Status", color=embed_color)
            embed.add_field(name="API Status", value=f"{status_emoji} {status_text}")

            component_lines = []
            for component in components_data:
                component_name = component.get('name')
                component_status = component.get('status')
                component_emoji = ':green_circle:' if component_status.lower() == 'operational' else ':red_circle:'
                component_line = f"{component_emoji} **{component_name}**: {component_status}"
                component_lines.append(component_line)

            embed.add_field(name="System Status", value='\n'.join(component_lines), inline=False)

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            embed.set_footer(text=f"Sist Oppdatert: {current_time}")

            if channel:
                if EDIT_CHANNEL:
                    await channel.edit(name = f'{emoji}︱{CHANNEL_NAME}')

                last_message = None

                if last_message_id:
                    try:
                        last_message = await channel.fetch_message(last_message_id)
                    except discord.errors.NotFound:
                        pass

                if last_message:
                    try:
                        await last_message.edit(embed=embed)
                    except discord.errors.Forbidden:
                        new_message = await channel.send(embed=embed)
                        last_message_id = new_message.id
                else:
                    new_message = await channel.send(embed=embed)
                    last_message_id = new_message.id
        except Exception as e:
            print(f"En feil oppstod: {str(e)}")

        await asyncio.sleep(REFRESH_INTERVAL)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Vennligst oppgi alle nødvendige argumenter.')
    else:
        await ctx.send('Det oppsto en feil under utførelse av kommandoen.')

bot.run(TOKEN)