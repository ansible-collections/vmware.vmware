from ansible.module_utils.basic import env_fallback


def common_argument_spec():
    return dict(
        hostname=dict(
            type='str',
            required=False,
            fallback=(env_fallback, ['VMWARE_HOST']),
        ),
        username=dict(
            type='str',
            aliases=['user', 'admin'],
            required=False,
            fallback=(env_fallback, ['VMWARE_USER'])
        ),
        password=dict(
            type='str',
            aliases=['pass', 'pwd'],
            required=False,
            no_log=True,
            fallback=(env_fallback, ['VMWARE_PASSWORD'])
        ),
        port=dict(
            type='int',
            default=443,
            fallback=(env_fallback, ['VMWARE_PORT'])
        ),
        validate_certs=dict(
            type='bool',
            required=False,
            default=True,
            fallback=(env_fallback, ['VMWARE_VALIDATE_CERTS'])
        ),
        proxy_protocol=dict(
            type='str',
            default='https',
            choices=['https', 'http'],
            aliases=['protocol']
        ),
        proxy_host=dict(
            type='str',
            required=False,
            default=None,
            fallback=(env_fallback, ['VMWARE_PROXY_HOST'])
        ),
        proxy_port=dict(
            type='int',
            required=False,
            default=None,
            fallback=(env_fallback, ['VMWARE_PROXY_PORT'])
        ),
    )