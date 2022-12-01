import discord
from discord.ext import commands
import pymongo
import os

client = pymongo.MongoClient(
    f'mongodb+srv://Senjienji:{os.getenv("PASSWORD")}@senjienji.czypcav.mongodb.net/?retryWrites=true&w=majority',
    server_api = pymongo.server_api.ServerApi('1'),
)
db = client.counter_bot
counter_col = db.counter
prefix_col = db.prefix

class MinimalHelpCommand(commands.MinimalHelpCommand):
    async def send_pages(self):
        await self.context.reply(embed = discord.Embed(
            title = 'Help',
            description = self.paginator.pages[0],
            color = 0xffffff
        ).set_footer(
            text = self.context.author.display_name,
            icon_url = self.context.author.display_avatar.url
        ))

bot = commands.Bot(
    command_prefix = lambda bot, message: prefix_col.find_one({'guild': message.guild.id})['prefix'],
    help_command = MinimalHelpCommand(),
    allowed_mentions = discord.AllowedMentions.none(),
    intents = discord.Intents(
        guilds = True,
        messages = True,
        message_content = True
    )
)

@bot.event
async def on_connect():
    print('Connected')

@bot.event
async def on_ready():
    print('Ready')

@bot.event
async def on_message(message):
    if message.guild == None: return
    
    if prefix_col.find_one({'guild': message.guild.id}) == None:
        prefix_col.insert_one({
            'guild': message.guild.id,
            'prefix': '&'
        })
    if counter_col.find_one({'guild': message.guild.id}) == None:
        counter_col.insert_one({
            'guild': message.guild.id,
            'channels': []
        })
    if message.channel.id in counter_col.find_one({'guild': message.guild.id})['channels']:
        if not message.content.isnumeric() or int(message.content) != int([i async for i in message.channel.history(limit = 1, before = message)][0].content) + 1:
            await message.delete()
    else:
        await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    if after.channel.id not in counter_col.find_one({'guild': message.guild.id})['channels'] or before.content == after.content: return
    
    if not after.content.isnumeric() or int(message.content) != int([i async for i in after.channel.history(limit = 1, before = after)][0].content) + 1:
        await message.delete()

@bot.command()
async def channels(ctx):
    await ctx.reply(embed = discord.Embed(
        title = 'Channels',
        description = '\n'.join(
            f'{index}. {channel.mention}' for index, channel in enumerate(
                filter(
                    lambda i: i != None, (
                        ctx.guild.get_channel(i) for i in counter_col.find_one({
                            'guild': ctx.guild.id
                        })['channels']
                    )
                ), start = 1
            )
        ) or 'None',
        color = 0xffffff
    ).set_footer(
        text = ctx.author.display_name,
        icon_url = ctx.author.display_avatar.url
    ))

@bot.command()
@commands.has_guild_permissions(manage_guild = True)
async def add(ctx, channel: discord.TextChannel):
    channels = counter_col.find_one({'guild': ctx.guild.id})['channels']
    if channel.id in channels:
        await ctx.reply(f'{channel.mention} is already added.')
    else:
        channels.append(channel.id)
        counter_col.find_one_and_update(
            {'guild': ctx.guild.id},
            {'$set': {'channels': channels}}
        )
        await ctx.reply(f'{channel.mention} added.')

@bot.command()
@commands.has_guild_permissions(manage_guild = True)
async def remove(ctx, channel: discord.TextChannel):
    channels = counter_col.find_one({'guild': ctx.guild.id})['channels']
    if channel.id in channels:
        del channels[channel.id]
        counter_col.find_one_and_update(
            {'guild': ctx.guild.id},
            {'$set': {'channels': channels}}
        )
        await ctx.reply(f'{channel.mention} removed.')
    else:
        await ctx.reply(f'{channel.mention} not found.')

@bot.command()
async def prefix(ctx, prefix = ''):
    if prefix == '':
        await ctx.reply(f'current prefix is `{bot.command_prefix(bot, ctx.message)}`')
    elif ctx.author.guild_permissions.manage_guild:
        prefix_col.find_one_and_update(
            {'guild': ctx.guild.id},
            {'$set': {'prefix': prefix}}
        )
        await ctx.reply(f'prefix changed to `{bot.command_prefix(bot, ctx.message)}`')

bot.run(os.environ['DISCORD_TOKEN'])
