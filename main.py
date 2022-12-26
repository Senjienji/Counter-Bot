import discord
from discord.ext import commands
import pymongo
import os

client = pymongo.MongoClient(
    f'mongodb+srv://Senjienji:{os.environ["PASSWORD"]}@senjienji.czypcav.mongodb.net/?retryWrites=true&w=majority',
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
        ).set_author(
            name = self.context.author,
            url = f'https://discord.com/users/{self.context.author.id}',
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
    
    doc = counter_col.find_one({'guild': message.guild.id})
    if doc == None:
        doc = {
            'guild': message.guild.id,
            'channels': []
        }
        counter_col.insert_one(doc)
    
    if message.channel.id in doc['channels']:
        if not message.content:
            await message.delete()
            return
        
        text = message.content.split()[0]
        if not text.isnumeric():
            await message.delete()
            return
        
        history = [i async for i in message.channel.history(
            limit = 1,
            before = message
        )]
        if history:
            count = int(history[0].content.split()[0])
        else:
            count = 0
        
        if int(text) != count + 1:
            await message.delete()
            return
    else:
        await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    if after.channel.id not in counter_col.find_one({'guild': after.guild.id})['channels']: return
    
    prev = int(before.content.split()[0])
    if not after.content:
        await after.delete()
        return
    
    next_text = after.content.split()[0]
    if next_text.isnumeric():
        next = int(next_text)
    else:
        await after.delete()
        return
    
    if prev == next: return
    
    history = [i async for i in before.channel.history(
        limit = 1,
        before = before
    )]
    if history:
        count = int(history[0].content.split()[0])
    else:
        count = 0
    
    if next != count + 1:
        await after.delete()
        return

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
        ) or f'Run {bot.command_prefix(bot, ctx.message)}{add.name} <channel> to add a counting channel!',
        color = 0xffffff
    ).set_author(
        name = ctx.author,
        url = f'https://discord.com/users/{ctx.author.id}',
        icon_url = ctx.author.display_avatar.url
    ))

@bot.command()
@commands.has_guild_permissions(manage_guild = True)
async def add(ctx, channel: discord.TextChannel):
    doc = counter_col.find_one({'guild': ctx.guild.id})
    channels = doc['channels']
    if channel.id in channels:
        await ctx.reply(f'{channel.mention} is already added.')
    else:
        channels.append(channel.id)
        counter_col.update_one(
            {'_id': doc['_id']},
            {'$set': {'channels': channels}}
        )
        await ctx.reply(f'{channel.mention} added.')

@bot.command()
@commands.has_guild_permissions(manage_guild = True)
async def remove(ctx, channel: discord.TextChannel):
    doc = counter_col.find_one({'guild': ctx.guild.id})
    channels = doc['channels']
    if channel.id in channels:
        del channels[channel.id]
        counter_col.update_one(
            {'_id': doc['_id']},
            {'$set': {'channels': channels}}
        )
        await ctx.reply(f'{channel.mention} removed.')
    else:
        await ctx.reply(f'{channel.mention} not found.')

@bot.command()
async def prefix(ctx, *, prefix = None):
    if not prefix:
        await ctx.reply(f'Current prefix is `{bot.command_prefix(bot, ctx.message)}`')
    elif ctx.author.guild_permissions.manage_guild:
        prefix_col.update_one(
            {'guild': ctx.guild.id},
            {'$set': {'prefix': prefix}}
        )
        await ctx.reply(f'Prefix changed to `{bot.command_prefix(bot, ctx.message)}`')

bot.run(os.environ['DISCORD_TOKEN'])
