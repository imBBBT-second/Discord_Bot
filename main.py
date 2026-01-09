import discord
from discord import app_commands
from discord.ext import commands
import datetime
import asyncio
import os

# 1. 봇 설정
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"슬래시 명령어 동기화 완료!")

bot = MyBot()

# 데이터 저장용
BAD_WORDS = ["운지", "부엉이 바위", "노무현", "응디", "부딱", "북딱", "느금마", "니애미"]
user_warnings = {}

# 공통 처벌 및 공지 로직 함수
async def apply_punishment(member, reason, channel):
    user_id = member.id
    user_warnings[user_id] = user_warnings.get(user_id, 0) + 1
    warn_count = user_warnings[user_id]
    
    punishment = ""
    duration = None

    # 네가 정한 단계별 처벌 수위
    if warn_count == 1:
        punishment = "타임아웃 1분"
        duration = datetime.timedelta(minutes=1)
    elif warn_count == 2:
        punishment = "타임아웃 1시간"
        duration = datetime.timedelta(hours=1)
    elif warn_count == 3:
        punishment = "타임아웃 12시간"
        duration = datetime.timedelta(hours=12)
    elif warn_count == 4:
        punishment = "타임아웃 24시간"
        duration = datetime.timedelta(days=1)
    elif warn_count == 5:
        punishment = "서버 추방 (메시지 삭제 포함)"
    elif warn_count >= 6:
        punishment = "서버 차단 (메시지 삭제 포함)"

    # [양식]에 맞춘 공지 생성
    notice_text = (
        f"@here\n"
        f"# 경고 공지\n"
        f"# {member.mention}\n"
        f"## 사유 : {reason}\n"
        f"## 강도 : {punishment}\n"
        f"### 날짜 : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    notice_msg = await channel.send(notice_text)

    # 실제 처벌 실행
    try:
        if warn_count <= 4:
            await member.timeout(duration, reason=reason)
        elif warn_count == 5:
            await member.kick(reason=reason)
        elif warn_count >= 6:
            await member.ban(reason=reason, delete_message_days=7)
    except Exception as e:
        print(f"처벌 실행 중 오류: {e}")

    # 공지는 3분 후 삭제
    await asyncio.sleep(180)
    try:
        await notice_msg.delete()
    except:
        pass

@bot.event
async def on_ready():
    print(f'🛡️ {bot.user.name} 관리 시스템 가동 중!')

# 금지어 감지 이벤트
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    if any(word in message.content for word in BAD_WORDS):
        await message.delete()
        await apply_punishment(message.author, "문제가 되는 메시지 감지", message.channel)
    
    await bot.process_commands(message)

# --- 슬래시 명령어 영역 ---

# [추가] 직접 경고 주기 명령어
@bot.tree.command(name="경고", description="관리자가 직접 유저에게 경고 스택을 부여합니다.")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, 대상자: discord.Member, 사유: str):
    await interaction.response.send_message(f"경고 부여 성공 : {대상자.display_name}", ephemeral=True)
    # 공통 처벌 로직 호출
    await apply_punishment(대상자, 사유, interaction.channel)

@bot.tree.command(name="경고확인", description="유저의 경고 횟수를 확인합니다.")
async def check_warn(interaction: discord.Interaction, 대상자: discord.Member = None):
    target = 대상자 or interaction.user
    count = user_warnings.get(target.id, 0)
    await interaction.response.send_message(f"{target.display_name}님의 현재 경고 스택 : `{count}`회", ephemeral=True)

@bot.tree.command(name="초기화", description="유저의 경고 스택을 초기화합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def reset_warn(interaction: discord.Interaction, 대상자: discord.Member):
    user_warnings[대상자.id] = 0
    await interaction.response.send_message(f"경고 초기화 성공 : {대상자.mention}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("명령어 사용 권한 없음", ephemeral=True)

token = os.getenv('TOKEN')

if __name__ == "__main__":
    if token:
        bot.run(token)
    else:
        # 만약 환경 변수가 없다면 여기에 직접 토큰을 넣어서 테스트할 수도 있어
        print("환경 변수 "TOKEN" 미발견)
