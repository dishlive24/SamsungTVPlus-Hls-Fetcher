import requests
import gzip
import json
import os
import logging
from io import BytesIO

OUTPUT_DIR = "samsungtvplus"
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
SAMSUNG_URL = 'https://github.com/matthuisman/i.mjh.nz/raw/refs/heads/master/SamsungTVPlus/.channels.json.gz'
STREAM_URL_TEMPLATE = 'https://jmp2.uk/sam-{id}.m3u8'
EPG_URL_TEMPLATE = 'https://github.com/matthuisman/i.mjh.nz/raw/master/SamsungTVPlus/{region}.xml.gz'
REGIONS = ['us', 'ca', 'gb', 'au', 'de', 'all']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_url(url, is_json=True, is_gzipped=False):
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.content

        if is_gzipped:
            with gzip.GzipFile(fileobj=BytesIO(content), mode='rb') as f:
                content = f.read().decode('utf-8')
        else:
            content = content.decode('utf-8')

        return json.loads(content) if is_json else content
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

def format_extinf(channel_id, tvg_id, tvg_chno, tvg_name, group_title, display_name):
    return (f'#EXTINF:-1 channel-id="{channel_id}" tvg-id="{tvg_id}" '
            f'tvg-chno="{tvg_chno or ""}" tvg-name="{tvg_name}" '
            f'tvg-logo="" group-title="{group_title}",{display_name}\n')

def write_m3u_file(filename, content):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    with open(os.path.join(OUTPUT_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(content)

def generate_samsungtvplus_m3u():
    data = fetch_url(SAMSUNG_URL, is_json=True, is_gzipped=True)
    if not data or 'regions' not in data:
        logging.error("Failed to fetch SamsungTVPlus data.")
        return

    for region in REGIONS:
        logging.info(f"📺 Generating for region: {region}")
        epg_url = EPG_URL_TEMPLATE.replace('{region}', region)
        lines = [f'#EXTM3U url-tvg="{epg_url}"\n']
        is_all = region == 'all'
        channels = {}

        if is_all:
            for region_key, region_data in data['regions'].items():
                group_name = region_data.get('name', region_key.upper())
                for ch_id, ch_info in region_data.get('channels', {}).items():
                    key = f"{ch_id}-{region_key}"
                    channels[key] = {**ch_info, 'region': region_key, 'group': group_name, 'orig_id': ch_id}
        else:
            region_data = data['regions'].get(region)
            if not region_data:
                logging.warning(f"No data for region: {region}")
                continue
            group_name = region_data.get('name', region.upper())
            for ch_id, ch_info in region_data.get('channels', {}).items():
                channels[ch_id] = {**ch_info, 'region': region, 'group': group_name, 'orig_id': ch_id}

        sorted_channels = sorted(channels.items(), key=lambda x: x[1].get('name', '').lower())

        for ch_key, ch in sorted_channels:
            extinf = format_extinf(ch_key, ch['orig_id'], ch.get('chno'), ch.get('name', 'Unknown'), ch['group'], ch.get('name', 'Unknown'))
            stream = STREAM_URL_TEMPLATE.replace('{id}', ch['orig_id'])
            lines.append(extinf)
            lines.append(stream + '\n')

        write_m3u_file(f"samsungtvplus_{region}.m3u", ''.join(lines))
        logging.info(f"✅ Done: samsungtvplus_{region}.m3u")

if __name__ == "__main__":
    generate_samsungtvplus_m3u()
