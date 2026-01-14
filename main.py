import discord
from discord import app_commands
from discord.ext import commands
import datetime
import asyncio
import os

# 1. 봇 클래스 설정
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ 슬래시 명령어 동기화 완료!")

bot = MyBot()

# 데이터 및 설정
BAD_WORDS = ["운지", "부엉이 바위", "응디", "부딱", "북딱", "느금마", "니애미"]
user_warnings = {}

# [공통 로직] 처벌 및 특정 채널 공지 함수
async def apply_punishment(member: discord.Member, reason: str, current_channel: discord.TextChannel):
    user_id = member.id
    user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
    warn_count = user_warnings[user_id]
    
    # 환경 변수에서 공지 채널 ID 가져오기
    notice_channel_id = os.getenv('NOTICE_CHANNEL_ID')
    
    # 공지 보낼 채널 결정 (환경 변수 설정이 없으면 현재 채널에 보냄)
    target_channel = current_channel
    if notice_channel_id:
        try:
            target_channel = bot.get_channel(int(notice_channel_id)) or current_channel
        except:
            target_channel = current_channel

    punishment = ""
    duration = None

    # 단계별 처벌 수위
    if warn_count == 1:
        punishment = "타임아웃 1분"; duration = datetime.timedelta(minutes=1)
    elif warn_count == 2:
        punishment = "타임아웃 1시간"; duration = datetime.timedelta(hours=1)
    elif warn_count == 3:
        punishment = "타임아웃 12시간"; duration = datetime.timedelta(hours=12)
    elif warn_count == 4:
        punishment = "타임아웃 24시간"; duration = datetime.timedelta(days=1)
    elif warn_count == 5:
        punishment = "서버 추방 (메시지 삭제 포함)"
    elif warn_count >= 6:
        punishment = "서버 차단 (메시지 삭제 포함)"

    # [양식] 공지 텍스트
    notice_text = (
        f"@here\n"
        f"# 경고 공지\n"
        f"# {member.mention}\n"
        f"## 사유 : {reason}\n"
        f"## 강도 : {punishment}\n"
        f"### 날짜 : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # 지정된 채널에 공지 전송
    notice_msg = await target_channel.send(notice_text)

    # 실제 처벌 실행
    try:
        if warn_count <= 4:
            await member.timeout(duration, reason=reason)
        elif warn_count == 5:
            await member.kick(reason=reason)
        elif warn_count >= 6:
            await member.ban(reason=reason, delete_message_days=7)
    except Exception as e:
        print(f"❌ 처벌 적용 오류: {e}")

@bot.event
async def on_ready():
    print(f'🛡️ {bot.user.name} 관리 시스템 가동 중!')

@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(word in message.content for word in BAD_WORDS):
        await message.delete()
        await apply_punishment(message.author, "금지어 사용 안내 규칙 위반", message.channel)
    await bot.process_commands(message)

# --- 슬래시 명령어 ---

@bot.tree.command(name="경고", description="직접 경고 부여")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, 대상자: discord.Member, 사유: str):
    # 명령어 응답은 사용자에게만 보이게(ephemeral) 보냄
    await interaction.response.send_message(f"{대상자.display_name} : 경고 부여 완료", ephemeral=True)
    await apply_punishment(대상자, 사유, interaction.channel)

@bot.tree.command(name="초기화", description="경고 초기화")
@app_commands.checks.has_permissions(administrator=True)
async def reset_warn(interaction: discord.Interaction, 대상자: discord.Member):
    user_warnings[대상자.id] = 0
    await interaction.response.send_message(f"{대상자.mention} : 경고 초기화")

# 봇 실행
token = os.getenv('TOKEN')
if token:
    bot.run(token)
else:
    print("❌ 오류: TOKEN 환경 변수가 없어!")
