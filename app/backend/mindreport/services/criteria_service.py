"""
기능: 마음 리포트 생성 기준(주간 5개, 월간 20개 대화)을 검사하는 핵심 비즈니스 로직(Service)을 담당하는 파일입니다. views.py에서 호출하여 사용합니다.
"""
from datetime import datetime, timedelta
from django.utils import timezone
from chat.models import ChatMessage

class ReportCriteriaService:
    """
    마음 리포트 생성 기준을 검사하는 서비스 클래스
    기획 기준: 주간 5개 이상, 월간 20개 이상의 '사용자 메시지(ChatMessage)'
    """

    @staticmethod
    def get_weekly_chat_count(user, target_date=None):
        if target_date is None:
            target_date = timezone.now().date()
            
        # 주간 기준: target_date가 속한 주의 월요일 ~ 일요일
        start_of_week = target_date - timedelta(days=target_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # 날짜 범위 설정 (자정부터 다음날 자정 직전까지)
        start_datetime = timezone.make_aware(datetime.combine(start_of_week, datetime.min.time()))
        end_datetime = timezone.make_aware(datetime.combine(end_of_week, datetime.max.time()))
        
        # 사용자가 보낸 메시지만 카운트 (role='user')
        count = ChatMessage.objects.filter(
            session__user=user,
            role='user',
            created_at__gte=start_datetime,
            created_at__lte=end_datetime
        ).count()
        
        return count

    @staticmethod
    def get_monthly_chat_count(user, year=None, month=None):
        if year is None or month is None:
            now = timezone.now()
            year = now.year if year is None else year
            month = now.month if month is None else month
            
        # 사용자가 보낸 메시지만 카운트 (role='user')
        count = ChatMessage.objects.filter(
            session__user=user,
            role='user',
            created_at__year=year,
            created_at__month=month
        ).count()
        
        return count

    @staticmethod
    def check_weekly_report_eligibility(user, target_date=None):
        """주간 리포트 생성 기준(사용자 메시지 5개 이상) 충족 여부 확인"""
        required_count = 5
        current_count = ReportCriteriaService.get_weekly_chat_count(user, target_date)
        
        return {
            "is_eligible": current_count >= required_count,
            "current_count": current_count,
            "required_count": required_count,
            "missing_count": max(0, required_count - current_count)
        }

    @staticmethod
    def check_monthly_report_eligibility(user, year=None, month=None):
        """월간 리포트 생성 기준(사용자 메시지 20개 이상) 충족 여부 확인"""
        required_count = 20
        current_count = ReportCriteriaService.get_monthly_chat_count(user, year, month)
        
        return {
            "is_eligible": current_count >= required_count,
            "current_count": current_count,
            "required_count": required_count,
            "missing_count": max(0, required_count - current_count)
        }
