from ipware import get_client_ip



# If/when Cloudflare is added: pass proxy_trusted_ips=CLOUDFLARE_IP_RANGES so
# ipware skips Cloudflare's edge IP (rightmost) and returns the client IP instead.
def client_ip_key(group, request):
    # Nginx appends $remote_addr (the real connecting IP) to XFF,
    # so rightmost is always the real client when only nginx is in the chain.
    ip, _ = get_client_ip(request, proxy_order='right-most')
    return ip or '0.0.0.0'
