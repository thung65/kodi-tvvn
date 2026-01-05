# -*- coding: UTF-8 -*-
import os, re, sys, json, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
import urllib.parse as urllib_parse
import urllib.request as urllib_request

# --- Cấu hình Addon ---
addon = xbmcaddon.Addon('plugin.video.tvvn')
home = xbmcvfs.translatePath(addon.getAddonInfo('path'))
fanart = xbmcvfs.translatePath(os.path.join(home, 'fanart.jpg'))
datafile = xbmcvfs.translatePath(os.path.join(home, 'data.json'))

# Mở file dữ liệu
with open(datafile, "r", encoding="utf8") as f:
    data = json.loads(f.read())

def get_params():
    param = {}
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        pairs = paramstring.replace('?', '').split('&')
        for p in pairs:
            split = p.split('=')
            if len(split) == 2: param[split[0]] = split[1]
    return param

def construct_menu(namex):
    # Lấy danh sách từ JSON
    menu_items = data['directories'][namex]['content']
    
    # Sắp xếp theo yêu cầu: All lên đầu, International/Oversea xuống cuối
    all_items = [i for i in menu_items if "all" in str(i.get('id','')).lower()]
    inter_items = [i for i in menu_items if any(x in str(i.get('id','')).lower() for x in ["oversea", "international"])]
    others = [i for i in menu_items if i not in all_items and i not in inter_items]
    
    sorted_list = all_items + others + inter_items

    for item in sorted_list:
        item_type = item.get('type', '')
        item_id = item.get('id', '')
        if item_type in ["chn", "chn_"]:
            add_chn_link(item_id)
        elif item_type in ["dir", "dir_"]:
            add_dir_link(item_id)
            
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def add_chn_link(chn_id):
    if chn_id not in data['channels']: return
    info = data['channels'][chn_id]
    title = info['title']
    icon = xbmcvfs.translatePath(os.path.join(home, 'resources', 'logos', info.get('logo', 'default.png')))
    
    # Link gọi hàm mode=1 để phát video
    url = f"{sys.argv[0]}?mode=1&chn={chn_id}"
    
    liz = xbmcgui.ListItem(title)
    liz.setInfo(type="video", infoLabels={"title": title, "plot": info.get('desc', '')})
    liz.setArt({"thumb": icon, "icon": icon, "fanart": fanart})
    liz.setProperty('IsPlayable', 'true') # Giúp Kodi hiểu đây là file video
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=liz)

def add_dir_link(dir_id):
    if dir_id not in data['directories']: return
    info = data['directories'][dir_id]
    title = f"[B]{info['title']}[/B]"
    icon = xbmcvfs.translatePath(os.path.join(home, 'resources', 'logos', info.get('logo', 'default.png')))
    
    url = f"{sys.argv[0]}?mode=2&chn={dir_id}"
    liz = xbmcgui.ListItem(title)
    liz.setArt({"thumb": icon, "icon": icon, "fanart": fanart})
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=liz, isFolder=True)

def play_link(chn_id):
    chn = data['channels'][chn_id]
    play_type = chn['src']['playpath']
    ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    full_url = ""

    # Dialog chờ để người dùng không tưởng bị treo
    pDialog = xbmcgui.DialogProgress()
    pDialog.create('TVVN', 'Đang kết nối luồng phát...')

    try:
        # --- XỬ LÝ VTVGO (Hỗ trợ VTV1 -> VTV9) ---
        if play_type == "m3u8_vtvgo":
            page_url = chn['src']['page_url']
            headers = {'User-Agent': ua, 'Referer': 'https://vtvgo.vn/'}
            req = urllib_request.Request(page_url, headers=headers)
            html = urllib_request.urlopen(req, timeout=10).read().decode('utf-8')
            
            # Regex tìm link token mới nhất
            match = re.search(r"var\s+link\s*=\s*'(.*?)'", html)
            if match:
                stream_url = match.group(1)
                full_url = f"{stream_url}|User-Agent={ua}&Referer=https://vtvgo.vn/"

        # --- XỬ LÝ TVNET / VTC ---
        elif play_type == "m3u8_tvnet":
            page_id = chn['src']['page_id']
            api_url = f"http://au.tvnet.gov.vn/kenh-truyen-hinh/{page_id}"
            req = urllib_request.Request(api_url, headers={'User-Agent': ua})
            html = urllib_request.urlopen(req, timeout=10).read().decode('utf-8')
            
            # Lấy link từ data-file
            match = re.search(r'data-file="(.*?)"', html)
            if match:
                full_url = f"{match.group(1)}|User-Agent={ua}"

    except Exception as e:
        xbmcgui.Dialog().ok("Lỗi", "Kênh hiện tại đang bảo trì hoặc lỗi kết nối.")

    pDialog.close()

    if full_url:
        liz = xbmcgui.ListItem(path=full_url)
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)
        xbmc.Player().play(full_url)

# --- Điều hướng mode ---
params = get_params()
mode = params.get('mode')
chn_id = params.get('chn')

if mode is None:
    construct_menu("root")
elif int(mode) == 1:
    play_link(chn_id)
elif int(mode) == 2:
    construct_menu(chn_id)

