from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.star.filter.event_message_type import EventMessageType  # 导入枚举
import json
import requests
from typing import Optional

@register("astrbot_plugin_qqgroup_notice", "陌筏", "群成员入群/退群通知插件（仅NapCat）", "1.0.0", "https://github.com/New-WeiLai/astrbot_plugin_qqgroup_notice")
class GroupNoticePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config = context.get_config() or {}
        logger.info("群通知插件已加载，配置：%s", self.config)

    def get_nickname(self, user_id: int) -> Optional[str]:
        if not self.config.get("enable_nickname", False):
            return None
        host = self.config.get("napcat_http_host", "127.0.0.1")
        port = self.config.get("napcat_http_port", 3000)
        try:
            resp = requests.get(
                f"http://{host}:{port}/get_stranger_info",
                params={"user_id": user_id},
                timeout=3
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "ok":
                    return data.get("data", {}).get("nickname", str(user_id))
        except Exception as e:
            logger.warning(f"获取昵称失败: {e}")
        return str(user_id)

    def format_message(self, template: str, **kwargs) -> str:
        if not self.config.get("enable_nickname", False):
            kwargs["nickname"] = kwargs.get("user_id", "未知")
        return template.format(**kwargs)

    @filter.event_message_type(EventMessageType.ALL)  # 使用枚举，而非字符串
    async def on_all_events(self, event: AstrMessageEvent):
        raw = event.message_obj.raw_message

        # ---------- 安全解析为字典 ----------
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return
        elif isinstance(raw, dict):
            data = raw
        else:
            return

        if not isinstance(data, dict):
            return

        # 只处理通知事件
        if data.get('post_type') != 'notice':
            return

        notice_type = data.get('notice_type')
        group_id = data.get('group_id')
        user_id = data.get('user_id')
        if not user_id:
            return

        welcome_tpl = self.config.get("welcome_message", "🎉 欢迎新成员 {nickname}！({way})")
        leave_tpl = self.config.get("leave_message", "👋 成员 {nickname} 已{reason}")

        # ---------- 入群处理 ----------
        if notice_type == 'group_increase':
            sub_type = data.get('sub_type')
            operator_id = data.get('operator_id')
            if sub_type == 'approve':
                way = "通过邀请或申请入群"
            elif sub_type == 'invite':
                way = f"被 {operator_id or '未知'} 邀请入群"
            else:
                way = "主动入群"

            nickname = self.get_nickname(user_id) if self.config.get("enable_nickname") else str(user_id)
            msg = self.format_message(
                welcome_tpl,
                user_id=user_id,
                nickname=nickname or str(user_id),
                group_id=group_id,
                way=way,
                inviter_id=operator_id
            )
            yield event.plain_result(msg)
            logger.info(f"群 {group_id} 新成员 {user_id} 入群，方式: {way}")

        # ---------- 退群处理 ----------
        elif notice_type == 'group_decrease':
            operator_id = data.get('operator_id')
            sub_type = data.get('sub_type')
            if sub_type == 'leave':
                reason = "主动退群"
            elif sub_type == 'kick':
                reason = f"被管理员 {operator_id} 踢出"
            else:
                reason = "由于未知原因退出"

            nickname = self.get_nickname(user_id) if self.config.get("enable_nickname") else str(user_id)
            msg = self.format_message(
                leave_tpl,
                user_id=user_id,
                nickname=nickname or str(user_id),
                group_id=group_id,
                reason=reason,
                operator_id=operator_id
            )
            yield event.plain_result(msg)
            logger.info(f"群 {group_id} 成员 {user_id} 退群，原因: {reason}")

    async def terminate(self):
        logger.info("群通知插件已卸载")