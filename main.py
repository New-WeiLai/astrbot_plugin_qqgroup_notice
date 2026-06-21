from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import json

@register("astrbot_plugin_group_notice", "陌筏", "群成员入群/退群通知插件（仅napcat）", "1.0.0", "https://github.com/new-weilai/astrbot_qqgroup_notice")
class GroupNoticePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("群通知插件已加载")

    @filter.event_message_type(EventMessageType.ALL)
    async def on_group_member_change(self, event: AstrMessageEvent):
        """监听群成员变动（入群/退群）"""
        raw_msg = event.message_obj.raw_message
        
        # 尝试解析 JSON（NapCat/OneBot 的事件数据）
        try:
            data = json.loads(raw_msg) if isinstance(raw_msg, str) else raw_msg
        except:
            return  # 不是 JSON 格式的消息，忽略
        
        # 只处理 notice 类型事件
        if data.get('post_type') != 'notice':
            return
        
        notice_type = data.get('notice_type')
        group_id = data.get('group_id')
        user_id = data.get('user_id')
        
        # ===== 处理退群事件 =====
        if notice_type == 'group_decrease':
            operator_id = data.get('operator_id')
            sub_type = data.get('sub_type')
            
            if sub_type == 'leave':
                reason = "主动退群"
            elif sub_type == 'kick':
                reason = f"被管理员 {operator_id} 踢出"
            else:
                reason = "由于未知原因退出"
            
            yield event.plain_result(f"👋 成员 {user_id} 已{reason}")
            logger.info(f"群 {group_id} 成员 {user_id} 退群，原因: {reason}")
        
        # ===== 处理入群事件 =====
        elif notice_type == 'group_increase':
            sub_type = data.get('sub_type')
            
            if sub_type == 'approve':
                way = "通过邀请或申请入群"
            elif sub_type == 'invite':
                inviter_id = data.get('operator_id')
                way = f"被 {inviter_id} 邀请入群"
            else:
                way = "主动入群"
            
            yield event.plain_result(f"🎉 欢迎新成员 {user_id}！({way})")
            logger.info(f"群 {group_id} 有新成员 {user_id} 加入，方式: {way}")

    async def terminate(self):
        logger.info("群通知插件已卸载")
