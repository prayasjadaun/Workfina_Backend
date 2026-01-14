import firebase_admin
from firebase_admin import credentials, messaging
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class SimpleFCM:
    _app = None
    
    @classmethod
    def initialize(cls):
        if not cls._app:
            try:
                if firebase_admin._apps:
                    cls._app = firebase_admin.get_app()
                    logger.info("Using existing Firebase Admin app")
                    return

                # Get service account path from settings
                service_account_path = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_KEY', 'firebase-service-account.json')

                logger.info(f"Attempting to initialize Firebase with path: {service_account_path}")

                if os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                    cls._app = firebase_admin.initialize_app(cred)
                    logger.info(f"Firebase Admin initialized successfully with service account: {service_account_path}")
                else:
                    error_msg = f"Firebase service account file not found: {service_account_path}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

            except Exception as e:
                logger.error(f"Firebase initialization failed: {e}", exc_info=True)
                raise e
    
    @classmethod
    def send_to_token(cls, token, title, body, data=None, play_sound=True):
        """Send notification to single FCM token"""
        logger.info(f"Sending notification to token: {token[:20]}... - Title: {title}")
        cls.initialize()

        try:
            # Android notification config with sound
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default' if play_sound else None,
                    channel_id='workfina_notifications'
                )
            )

            # iOS/APNs notification config with sound
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default' if play_sound else None,
                        badge=1
                    )
                )
            )

            # Convert all data values to strings (FCM requirement)
            string_data = {k: str(v) for k, v in (data or {}).items()}

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                android=android_config,
                apns=apns_config,
                data=string_data,
                token=token,
            )

            response = messaging.send(message)
            logger.info(f"FCM message sent successfully: {response}")

            return {
                'success': True,
                'message_id': response,
                'success_count': 1,
                'failure_count': 0
            }

        except Exception as e:
            logger.error(f"FCM send failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'success_count': 0,
                'failure_count': 1
            }
    
    @classmethod
    def send_multicast(cls, tokens, title, body, data=None, play_sound=True):
        """Send notification to multiple FCM tokens"""
        cls.initialize()

        try:
            # Android notification config with sound
            android_config = messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default' if play_sound else None,
                    channel_id='workfina_notifications'
                )
            )

            # iOS/APNs notification config with sound
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default' if play_sound else None,
                        badge=1
                    )
                )
            )

            # Convert all data values to strings (FCM requirement)
            string_data = {k: str(v) for k, v in (data or {}).items()}

            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                android=android_config,
                apns=apns_config,
                data=string_data,
                tokens=tokens,
            )

            response = messaging.send_multicast(message)
            logger.info(f"FCM multicast sent: {response.success_count}/{len(tokens)} successful")
            
            return {
                'success': response.success_count > 0,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'responses': response.responses
            }
            
        except Exception as e:
            logger.error(f"FCM multicast failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'success_count': 0,
                'failure_count': len(tokens)
            }