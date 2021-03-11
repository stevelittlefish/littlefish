"""
Health checks - simple status reporters for monitoring / status pages
"""

import logging
from abc import ABC, abstractmethod, abstractproperty
import datetime

from flask import Markup

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6


class HealthCheckException(Exception):
    pass


class HealthCheckError(HealthCheckException):
    pass


class HealthCheckWarning(HealthCheckException):
    pass


class _HealthCheckSchedule(ABC):
    @abstractmethod
    def should_run(self, dt):
        """
        :param dt: Datetime
        :return: Whether or not the healthcheck should run
        """
        pass


class AlwaysRun(_HealthCheckSchedule):
    def should_run(self, dt):
        return True


ALWAYS_RUN = AlwaysRun()


class IncludeDaysOfWeek(_HealthCheckSchedule):
    def __init__(self, days_of_week):
        """
        :param days_of_week: List of integers with day of week to
                             run the health checks (0 is Monday, 6 is Sunday)
        """
        self.days_of_week = days_of_week

    def should_run(self, dt):
        return dt.date().weekday in self.days_of_week


class ExcludeDaysOfWeek(_HealthCheckSchedule):
    def __init__(self, days_of_week):
        """
        :param days_of_week: List of integers with day of week to NOT
                             run the health checks (0 is Monday, 6 is Sunday)
        """
        self.days_of_week = days_of_week

    def should_run(self, dt):
        return dt.date().weekday() not in self.days_of_week


class DayInterval:
    def __init__(self, from_time, to_time, include=True):
        self.from_time = from_time
        self.to_time = to_time
        self.include = include

    def should_run(self, dt):
        time = dt.time()

        if self.from_time is not None and time < self.from_time:
            return not self.include

        if self.to_time is not None and time > self.to_time:
            return not self.include

        return self.include

    def __repr__(self):
        return '{} {} to {}'.format(
            'Include' if self.include else 'Exclude',
            self.from_time if self.from_time is not None else '0:00',
            self.to_time if self.to_time is not None else '24:00'
        )


class IncludeInterval(_HealthCheckSchedule):
    def __init__(self, from_day, from_time, to_day, to_time):
        if from_day < 0:
            raise ValueError('From day must be >= 0')
        if from_day > 6:
            raise ValueError('From day must be <= 6')
        if to_day < 0:
            raise ValueError('To day must be >= 0')
        if to_day > 6:
            raise ValueError('To day must be <= 6')

        self.from_day = from_day
        self.from_time = from_time
        self.to_day = to_day
        self.to_time = to_time

        self.daily_schedules = [None] * 7

        if from_day == to_day:
            if from_time == to_time:
                raise ValueError('From and to times are the same')
            elif from_time < to_time:
                # This only runs on a specific day
                self.daily_schedules[from_day] = DayInterval(from_time, to_time)
            else:
                # This only excludes a specific day
                for i in range(0, 7):
                    if i != from_day:
                        self.daily_schedules[i] = DayInterval(None, None)

                self.daily_schedules[from_day] = DayInterval(from_time, to_time, include=False)
        elif from_day < to_day:
            for i in range(0, 7):
                if i < from_day:
                    pass
                elif i == from_day:
                    self.daily_schedules[i] = DayInterval(from_time, None)
                elif i < to_day:
                    self.daily_schedules[i] = DayInterval(None, None)
                elif i == to_day:
                    self.daily_schedules[i] = DayInterval(None, to_time)
                # else pass
        else:
            assert to_day < from_day
            for i in range(0, 7):
                if i < to_day:
                    self.daily_schedules[i] = DayInterval(None, None)
                elif i == to_day:
                    self.daily_schedules[i] = DayInterval(None, to_time)
                elif i < from_day:
                    pass
                elif i == from_day:
                    self.daily_schedules[i] = DayInterval(from_time, None)
                else:
                    self.daily_schedules[i] = DayInterval(None, None)

        # print(self.daily_schedules)
    
    def should_run(self, dt):
        weekday = dt.date().weekday()
        daily_schedule = self.daily_schedules[weekday]
        
        if daily_schedule is None:
            return False
        
        return daily_schedule.should_run(dt)


class ExcludeInterval(IncludeInterval):
    def should_run(self, dt):
        return not super().should_run(dt)


class HealthCheck(ABC):
    @abstractproperty
    def name(self):
        pass

    @abstractmethod
    def check(self):
        """
        :return a success message (an exception will be raised if this fails)
        """
        pass
    
    @property
    def schedule(self):
        return ALWAYS_RUN

    def should_run(self, dt=None):
        if dt is None:
            dt = datetime.datetime.utcnow()

        return self.schedule.should_run(dt)


class HealthCheckResult:
    def __init__(self, name, status, message):
        self.name = name
        self.status = status
        self.message = message


def run_health_checks(health_checks):
    results = []
    
    for health_check in health_checks:
        if health_check.should_run():
            status = 'success'
            try:
                message = health_check.check()
            except HealthCheckError as e:
                message = str(e)
                status = 'error'
            except HealthCheckWarning as w:
                message = str(w)
                status = 'warning'

            results.append(HealthCheckResult(health_check.name, status, message))

    return results


def render_health_check_results(results):
    out = ['<table class="health-checks"><tbody>']
    for result in results:
        out.append(
            '<tr><th>{}</th><td class="{}">{}</td></tr>'.format(
                result.name, result.status, result.message
            )
        )
    out.append('</tbody></table>')
    
    return Markup(''.join(out))


def run_and_render_health_checks(health_checks=None):
    results = run_health_checks(health_checks)

    return render_health_check_results(results)
