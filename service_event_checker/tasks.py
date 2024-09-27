from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
from ServiceCheckers.ADOServiceChecker import ADOServiceChecker
from ServiceCheckers.AzureServiceChecker import AzureServiceChecker
from ServiceCheckers.GithubServiceChecker import GithubServiceChecker
from ServiceCheckers.O365ServiceChecker import O365ServiceChecker
from ServiceCheckers.ReToolServiceChecker import ReToolServiceChecker
from ServiceCheckers.SalesforceServiceChecker import SalesforceServiceChecker
from ServiceCheckers.SlackServiceChecker import SlackServiceChecker
from ServiceCheckers.SnowflakeServiceChecker import SnowflakeServiceChecker

def initialize_scheduler(app):
    """
    Initialize the background scheduler for periodic service checks.
    The scheduler runs each check every 10 minutes.
    """
    scheduler = BackgroundScheduler()

    # Use app.app_context() to ensure each job runs inside the Flask app context
    with app.app_context():
        scheduler.add_job(lambda: run_service_check(AzureServiceChecker, 'Azure', app.logger), 'interval', minutes=10)
        scheduler.add_job(lambda: run_service_check(GithubServiceChecker, 'GitHub', app.logger), 'interval', minutes=10)
        scheduler.add_job(lambda: run_service_check(O365ServiceChecker, 'Office 365', app.logger), 'interval', minutes=10)
        scheduler.add_job(lambda: run_service_check(ReToolServiceChecker, 'ReTool', app.logger), 'interval', minutes=10)
        scheduler.add_job(lambda: run_service_check(SalesforceServiceChecker, 'Salesforce', app.logger), 'interval', minutes=10)
        scheduler.add_job(lambda: run_service_check(SlackServiceChecker, 'Slack', app.logger), 'interval', minutes=10)
        scheduler.add_job(lambda: run_service_check(SnowflakeServiceChecker, 'Snowflake', app.logger), 'interval', minutes=10)
        scheduler.add_job(lambda: run_service_check(ADOServiceChecker, 'Azure DevOps', app.logger), 'interval', minutes=10)

    scheduler.start()
    app.scheduler = scheduler

def run_service_check(service_checker, service_name, logger):
    """
    Runs a service check for the given service checker and logs the result.
    """
    logger.info(f"Running service check for {service_name}")
    try:
        service_checker.check_service()
        logger.info(f"{service_name} service check completed successfully")
    except Exception as e:
        logger.error(f"Error during {service_name} service check: {str(e)}")
