import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


OAUTH_STATE_SESSION_KEY = 'social_oauth_states'
SUPPORTED_PROVIDERS = ('kakao', 'naver', 'google')


class SocialOAuthError(Exception):
    pass


def get_provider_config(provider):
    if provider not in SUPPORTED_PROVIDERS:
        raise SocialOAuthError('Unsupported social login provider.')

    config = settings.SOCIAL_LOGIN['providers'].get(provider, {})
    if not config.get('client_id'):
        raise SocialOAuthError('Social login provider is not configured.')

    return config


def get_provider_status():
    providers = settings.SOCIAL_LOGIN.get('providers', {})
    return {
        provider: {
            'enabled': bool(providers.get(provider, {}).get('client_id')),
            'redirect_uri': providers.get(provider, {}).get('redirect_uri', ''),
        }
        for provider in SUPPORTED_PROVIDERS
    }


def build_authorization_url(request, provider, next_path=''):
    config = get_provider_config(provider)
    state = secrets.token_urlsafe(32)
    states = request.session.get(OAUTH_STATE_SESSION_KEY, {})
    states[state] = {
        'provider': provider,
        'next': next_path or '',
    }
    request.session[OAUTH_STATE_SESSION_KEY] = states
    request.session.modified = True

    params = {
        'response_type': 'code',
        'client_id': config['client_id'],
        'redirect_uri': config['redirect_uri'],
        'state': state,
    }
    if config.get('scope'):
        params['scope'] = config['scope']
    params.update(config.get('authorization_params', {}))

    return f"{config['authorization_url']}?{urlencode(params)}"


def pop_validated_state(request, provider, state):
    states = request.session.get(OAUTH_STATE_SESSION_KEY, {})
    state_payload = states.pop(state, None)
    request.session[OAUTH_STATE_SESSION_KEY] = states
    request.session.modified = True

    if not state_payload or state_payload.get('provider') != provider:
        raise SocialOAuthError('Invalid or expired social login state.')

    return state_payload


def _request_json(url, method='GET', data=None, headers=None):
    body = None
    request_headers = headers or {}
    if data is not None:
        body = urlencode(data).encode('utf-8')
        request_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            **request_headers,
        }

    request = Request(url, data=body, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        raise SocialOAuthError(f'Social provider request failed: {detail}') from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SocialOAuthError('Social provider request failed.') from exc


def exchange_code_for_token(provider, code):
    config = get_provider_config(provider)
    payload = {
        'grant_type': 'authorization_code',
        'client_id': config['client_id'],
        'redirect_uri': config['redirect_uri'],
        'code': code,
    }
    if config.get('client_secret'):
        payload['client_secret'] = config['client_secret']

    token_data = _request_json(config['token_url'], method='POST', data=payload)
    if not token_data.get('access_token'):
        raise SocialOAuthError('Social provider did not return an access token.')
    return token_data


def fetch_profile(provider, access_token):
    config = get_provider_config(provider)
    return _request_json(
        config['profile_url'],
        headers={'Authorization': f'Bearer {access_token}'},
    )


def normalize_profile(provider, profile):
    if provider == 'kakao':
        kakao_account = profile.get('kakao_account') or {}
        kakao_profile = kakao_account.get('profile') or {}
        return {
            'provider_user_id': str(profile.get('id') or ''),
            'email': kakao_account.get('email') or '',
            'nickname': kakao_profile.get('nickname') or '',
            'raw_profile': profile,
        }

    if provider == 'naver':
        response = profile.get('response') or {}
        return {
            'provider_user_id': str(response.get('id') or ''),
            'email': response.get('email') or '',
            'nickname': response.get('nickname') or response.get('name') or '',
            'name': response.get('name') or '',
            'birthyear': response.get('birthyear') or '',
            'birthday': response.get('birthday') or '',
            'gender': response.get('gender') or '',
            'raw_profile': profile,
        }

    if provider == 'google':
        return {
            'provider_user_id': str(profile.get('sub') or ''),
            'email': profile.get('email') or '',
            'nickname': profile.get('name') or '',
            'name': profile.get('name') or '',
            'raw_profile': profile,
        }

    raise SocialOAuthError('Unsupported social login provider.')


def fetch_social_profile(provider, code):
    token_data = exchange_code_for_token(provider, code)
    profile = fetch_profile(provider, token_data['access_token'])
    normalized = normalize_profile(provider, profile)
    if not normalized.get('provider_user_id'):
        raise SocialOAuthError('Social provider profile has no user id.')
    return normalized
