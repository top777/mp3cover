import sys
import os
import requests
import urllib.parse
import time
import random
import re
import datetime
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB
from mutagen.mp3 import MP3

# 为打包后的程序保留控制台
if getattr(sys, 'frozen', False):
    import ctypes
    ctypes.windll.kernel32.AttachConsole(-1)

def show_usage_info():
    """显示程序使用说明"""
    print("=" * 80)
    print("MP3专辑封面下载器 - 使用说明")
    print("=" * 80)
    print("功能: 自动从QQ音乐、网易云音乐、酷狗音乐和酷我音乐下载MP3专辑封面并嵌入")
    print("      成功添加封面后可自动将文件重命名为 YYYYMMDD.原文件名.mp3 格式")
    print("      如文件已有封面，则只执行重命名操作（除非使用--no-rename选项）")
    print("\n可用命令行参数:")
    print("  path            - MP3文件或目录路径(默认为当前目录)")
    print("  --delay 秒数    - 设置每首歌曲处理间隔时间(秒)，默认0.5秒")
    print("  --no-rename     - 不重命名文件，仅添加封面")
    print("  --force-download - 即使已有封面也强制重新下载")
    print("  --verbose       - 显示详细的处理信息")
    print("\n使用示例:")
    print("  python mp3_cover_downloader.py D:\\音乐文件夹")
    print("  python mp3_cover_downloader.py 单个文件.mp3 --delay 1")
    print("  python mp3_cover_downloader.py --no-rename")
    print("  python mp3_cover_downloader.py --force-download --verbose")
    print("=" * 80)
    print()

def get_cover_from_qq(song_name, artist):
    """从QQ音乐获取专辑封面"""
    try:
        # 搜索歌曲
        keyword = urllib.parse.quote(f"{song_name} {artist}")
        search_url = f"https://c.y.qq.com/soso/fcgi-bin/search_for_qq_cp?w={keyword}&format=json&p=1&n=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://y.qq.com/',
            'Accept': 'application/json'
        }
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        try:
            data = response.json()
        except ValueError:
            print(f"QQ音乐API返回了无效的JSON数据")
            return None, None
            
        if data.get('code') == 0 and data.get('data') and data['data'].get('song') and data['data']['song'].get('list') and len(data['data']['song']['list']) > 0:
            song = data['data']['song']['list'][0]
            # 获取专辑mid
            album_mid = song.get('albummid')
            
            # 提取元数据
            metadata = {
                'title': song.get('songname', ''),
                'artist': ', '.join([singer.get('name', '') for singer in song.get('singer', [])]),
                'album': song.get('albumname', '')
            }
            
            if album_mid:
                # 构造专辑封面URL
                img_url = f"https://y.gtimg.cn/music/photo_new/T002R800x800M000{album_mid}.jpg"
                img_response = requests.get(img_url, headers=headers, timeout=10)
                if img_response.status_code == 200 and len(img_response.content) > 10000:  # 确保不是默认图片
                    return img_response.content, metadata
                
                # 备用小图URL
                img_url_small = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_mid}.jpg"
                img_response = requests.get(img_url_small, headers=headers, timeout=10)
                if img_response.status_code == 200 and len(img_response.content) > 5000:
                    return img_response.content, metadata
                    
            return None, metadata
    except Exception as e:
        print(f"QQ音乐API错误: {str(e)}")
    return None, None

def get_cover_from_netease(song_name, artist):
    """从网易云音乐获取专辑封面"""
    try:
        clean_song = re.sub(r'\(.*?\)|\[.*?\]', '', song_name).strip()
        clean_artist = re.sub(r'\(.*?\)|\[.*?\]', '', artist).strip()

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://music.163.com/',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {'s': f"{clean_song} {clean_artist}", 'type': 1, 'limit': 5, 'offset': 0}
        response = requests.post("https://music.163.com/api/cloudsearch/pc", headers=headers, data=data, timeout=10)
        response.raise_for_status()

        try:
            result = response.json()
        except ValueError:
            print(f"网易云音乐API返回了无效的JSON数据")
            return None, None

        if result.get('code') == 200 and result.get('result') and result['result'].get('songs'):
            songs = result['result']['songs']
            best_match = None
            best_score = -1
            for song in songs[:5]:
                song_name_api = song.get('name', '').lower()
                artists = [a.get('name', '').lower().strip('-., ') for a in song.get('ar', [])]

                if clean_song.lower() in song_name_api or song_name_api in clean_song.lower():
                    for a in artists:
                        if clean_artist.lower() in a or a in clean_artist.lower():
                            # 评分：优先精确匹配、歌手数少的结果
                            score = 0
                            if a == clean_artist.lower():
                                score += 10
                            if len(artists) == 1:
                                score += 5
                            if song_name_api == clean_song.lower():
                                score += 3
                            if score > best_score:
                                best_score = score
                                best_match = song

            if not best_match:
                best_match = songs[0]

            album = best_match.get('al', {})
            pic_url = album.get('picUrl', '')
            metadata = {
                'title': best_match.get('name', ''),
                'artist': ', '.join(a.get('name', '').strip('-., ') for a in best_match.get('ar', [])),
                'album': album.get('name', '')
            }

            if pic_url and pic_url.startswith('http'):
                img_response = requests.get(pic_url, timeout=10)
                if img_response.status_code == 200:
                    return img_response.content, metadata

            return None, metadata
    except Exception as e:
        print(f"网易云音乐API错误: {str(e)}")
    return None, None

def get_cover_from_kugou(song_name, artist):
    """从酷狗音乐获取专辑封面"""
    try:
        # 搜索歌曲 - 使用更可靠的API
        keyword = urllib.parse.quote(f"{song_name} {artist}")
        search_url = f"https://songsearch.kugou.com/song_search_v2?keyword={keyword}&page=1&pagesize=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.kugou.com/'
        }
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 检查响应内容是否为JSON
        try:
            data = response.json()
        except ValueError:
            print(f"酷狗音乐API返回了无效的JSON数据")
            return None, None
            
        if data.get('status') == 1 and data.get('data') and data['data'].get('lists') and len(data['data']['lists']) > 0:
            # 获取第一个匹配结果的hash和album_id
            song_info = data['data']['lists'][0]
            file_hash = song_info.get('FileHash')
            album_id = song_info.get('AlbumID')
            
            # 提取元数据
            metadata = {
                'title': song_info.get('SongName', ''),
                'artist': song_info.get('SingerName', ''),
                'album': song_info.get('AlbumName', '')
            }
            
            # 尝试从移动端API获取专辑封面
            if file_hash:
                img_url = None
                # 优先尝试移动端API
                try:
                    mobile_url = f"https://m.kugou.com/app/i/getSongInfo.php?cmd=playInfo&hash={file_hash}"
                    mobile_headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Referer': 'https://m.kugou.com/'
                    }
                    mr = requests.get(mobile_url, headers=mobile_headers, timeout=10)
                    mdata = mr.json()
                    if mdata.get('status') == 1:
                        img_url = mdata.get('imgUrl', '')
                except Exception:
                    pass
                # 备用：尝试PC端API
                if not img_url:
                    try:
                        song_url = f"https://wwwapi.kugou.com/yy/index.php?r=play/getdata&hash={file_hash}&platid=4&mid=00000000000000000000000000000000"
                        sr = requests.get(song_url, headers={
                            'User-Agent': 'Mozilla/5.0',
                            'Referer': f'https://www.kugou.com/song/#hash={file_hash}'
                        }, timeout=10)
                        sdata = sr.json()
                        if sdata.get('status') == 1 and sdata.get('data'):
                            img_url = sdata['data'].get('img', '')
                    except Exception:
                        pass
                if img_url and img_url.startswith('http'):
                    img_url = img_url.replace('{size}', '400')
                    img_response = requests.get(img_url, timeout=10)
                    if img_response.status_code == 200 and len(img_response.content) > 5000:
                        return img_response.content, metadata
            return None, metadata
    except Exception as e:
        print(f"酷狗音乐API错误: {str(e)}")
    return None, None

def get_cover_from_kuwo(song_name, artist):
    """从酷我音乐获取专辑封面"""
    try:
        keyword = urllib.parse.quote(f"{song_name} {artist}")
        encoded_ref = urllib.parse.quote(f"http://www.kuwo.cn/search/list?key={song_name} {artist}", safe='/:?=&')
        search_url = f"http://www.kuwo.cn/api/www/search/searchMusicBykeyWord?key={keyword}&pn=1&rn=1"

        session = requests.Session()
        # 先访问首页获取基础cookie
        session.get('http://www.kuwo.cn/', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # 再访问搜索页获取搜索相关cookie
        session.get(f'http://www.kuwo.cn/search/list?key={keyword}', headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        time.sleep(0.5)

        csrf_token = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(10))
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': encoded_ref,
            'csrf': csrf_token,
            'Cookie': f'kw_token={csrf_token}'
        }

        response = session.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            print(f"酷我音乐搜索API返回了无效的JSON数据")
            return None, None

        if data.get('success') == False:
            return None, None
            
        if data.get('code') == 200 and data.get('data') and data['data'].get('list') and len(data['data']['list']) > 0:
            # 获取第一个匹配结果的rid
            song_data = data['data']['list'][0]
            rid = song_data['rid']
            
            # 提取元数据
            metadata = {
                'title': song_data.get('name', ''),
                'artist': song_data.get('artist', ''),
                'album': song_data.get('album', '')
            }
            
            # 获取专辑封面
            album_url = f"http://www.kuwo.cn/api/www/music/musicInfo?mid={rid}&httpsStatus=1"
            album_response = session.get(album_url, headers=headers, timeout=10)
            try:
                album_data = album_response.json()
                if album_data.get('code') == 200 and album_data.get('data'):
                    img_url = album_data['data'].get('pic')
                    if img_url and img_url.startswith('http'):
                        img_response = requests.get(img_url, timeout=10)
                        if img_response.status_code == 200:
                            return img_response.content, metadata
            except ValueError:
                print(f"酷我音乐专辑API返回了无效的JSON数据")
            return None, metadata
    except Exception as e:
        print(f"酷我音乐API错误: {str(e)}")
    return None, None

def get_cover_from_bing(song_name, artist):
    """从必应图片搜索获取可能的专辑封面"""
    try:
        # 构造搜索关键词
        keyword = urllib.parse.quote(f"{song_name} {artist} album cover")
        search_url = f"https://www.bing.com/images/search?q={keyword}&form=HDRSC2"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 使用正则表达式提取图片URL
        # 匹配必应图片搜索结果中的图片URL
        img_urls = re.findall(r'https?://[^\s"]+?\.(?:jpg|jpeg|png)', response.text)
        
        # 过滤出可能的专辑封面链接
        cover_urls = []
        for url in img_urls:
            # 排除小图标和其他无关图片
            if 'album' in url.lower() or 'cover' in url.lower():
                if 'mmrb' in url or 'thumb' in url or 'favicon' in url:
                    continue
                cover_urls.append(url)
        
        # 如果没有找到特定的专辑封面，尝试找前几个图片
        if not cover_urls and img_urls:
            for url in img_urls[:5]:  # 取前5个
                if any(ext in url for ext in ['.jpg', '.jpeg', '.png']):
                    if 'mmrb' not in url and 'thumb' not in url and 'favicon' not in url:
                        cover_urls.append(url)
        
        # 尝试下载找到的图片
        for img_url in cover_urls[:3]:  # 最多尝试前3个
            try:
                img_response = requests.get(img_url, headers=headers, timeout=10)
                if img_response.status_code == 200 and len(img_response.content) > 5000:  # 至少5KB
                    print(f"从必应图片搜索找到可能的专辑封面")
                    return img_response.content
            except:
                continue
                
    except Exception as e:
        print(f"必应图片搜索错误: {str(e)}")
    return None

def download_cover(song_name, artist):
    # 尝试从不同平台获取封面
    print(f"正在为 {song_name} - {artist} 搜索封面...")
    
    # 先尝试QQ音乐
    cover_data, metadata = get_cover_from_qq(song_name, artist)
    if cover_data:
        print(f"从QQ音乐找到 {song_name} 的封面")
        return cover_data, metadata
    elif metadata:
        # 即使没有封面，但有元数据也返回
        return None, metadata
    
    # 再尝试网易云音乐
    cover_data, metadata = get_cover_from_netease(song_name, artist)
    if cover_data:
        print(f"从网易云音乐找到 {song_name} 的封面")
        return cover_data, metadata
    elif metadata:
        # 即使没有封面，但有元数据也返回
        return None, metadata
    
    # 再尝试酷狗音乐
    cover_data, metadata = get_cover_from_kugou(song_name, artist)
    if cover_data:
        print(f"从酷狗音乐找到 {song_name} 的封面")
        return cover_data, metadata
    elif metadata:
        # 即使没有封面，但有元数据也返回
        return None, metadata
    
    # 最后尝试酷我音乐
    cover_data, metadata = get_cover_from_kuwo(song_name, artist)
    if cover_data:
        print(f"从酷我音乐找到 {song_name} 的封面")
        return cover_data, metadata
    elif metadata:
        # 即使没有封面，但有元数据也返回
        return None, metadata
    
    # 如果专业音乐网站都找不到，尝试必应图片搜索
    print(f"专业音乐网站未找到封面，尝试从必应图片搜索获取...")
    cover_data = get_cover_from_bing(song_name, artist)
    if cover_data:
        print(f"从必应图片搜索找到可能的专辑封面")
        # 必应搜索只返回图片数据，不返回元数据
        return cover_data, None
    
    print(f"无法找到 {song_name} - {artist} 的专辑封面")
    return None, None

def has_cover_art(audio):
    """检查MP3文件是否已有专辑封面"""
    try:
        # 检查是否有APIC帧（专辑图片）
        for key in audio.keys():
            if key.startswith('APIC'):
                # 检查图片数据大小是否大于1KB
                if len(audio[key].data) > 1000:
                    return True
        return False
    except Exception as e:
        print(f"检查封面时出错: {str(e)}")
        return False

def rename_file_with_date_prefix(file_path):
    """
    重命名文件，在原文件名前增加当前年月日（YYYYMMDD）和小数点分隔符
    
    Args:
        file_path: 文件的完整路径
        
    Returns:
        str: 重命名后的文件路径，如果未重命名则返回原路径
    """
    try:
        # 获取当前日期，格式为YYYYMMDD
        current_date = datetime.datetime.now().strftime("%Y%m%d")
        
        # 获取文件目录和文件名
        file_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        
        # 检查文件名是否已经包含日期前缀
        date_pattern = r"^\d{8}\.|^\d{8}_\d+\."
        if re.match(date_pattern, file_name):
            print(f"{file_name}: 文件名已包含日期前缀，无需重命名")
            return file_path
        
        # 创建新文件名: YYYYMMDD.原文件名
        new_file_name = f"{current_date}.{file_name}"
        new_file_path = os.path.join(file_dir, new_file_name)
        
        # 如果新文件已存在，添加数字后缀
        suffix = 1
        while os.path.exists(new_file_path):
            new_file_name = f"{current_date}_{suffix}.{file_name}"
            new_file_path = os.path.join(file_dir, new_file_name)
            suffix += 1
        
        # 重命名文件
        os.rename(file_path, new_file_path)
        print(f"文件已重命名: {file_name} -> {new_file_name}")
        return new_file_path
    except Exception as e:
        print(f"重命名文件失败: {str(e)}")
        return file_path

def extract_info_from_filename(filename):
    """从文件名中提取艺术家和歌曲名信息"""
    # 去除.mp3扩展名
    basename = filename.replace('.mp3', '')
    
    # 检查是否有日期前缀，如果有则去除
    date_match = re.match(r'^\d{8}\.(.+)$|^\d{8}_\d+\.(.+)$', basename)
    if date_match:
        basename = date_match.group(1) if date_match.group(1) else date_match.group(2)
    
    # 按 "艺术家 - 歌曲名" 格式分割
    parts = basename.split(' - ')
    
    if len(parts) >= 2:
        artist = parts[0].strip()
        song_name = parts[1].strip()
    else:
        # 无法分割，可能没有按照格式命名
        artist = "Unknown"
        song_name = basename
    
    return artist, song_name

def process_mp3_file(file_path):
    try:
        print(f"开始处理: {os.path.basename(file_path)}")
        
        # 检查文件是否存在ID3标签，如果不存在则创建
        try:
            audio = ID3(file_path)
        except:
            print(f"{os.path.basename(file_path)}: 未找到ID3标签，创建新标签")
            # 创建新的ID3标签
            audio = ID3()
            audio.save(file_path)
            audio = ID3(file_path)
        
        # 读取MP3文件
        mp3_audio = MP3(file_path, ID3=ID3)
        
        # 获取歌曲信息
        song_name = ""
        artist = ""
        
        # 尝试从ID3标签获取信息
        if 'TIT2' in audio:
            song_name = str(audio['TIT2'])
            print(f"获取到歌曲名: {song_name}")
        
        if 'TPE1' in audio:
            artist = str(audio['TPE1'])
            print(f"获取到艺术家: {artist}")
        
        # 如果ID3标签中没有足够信息，尝试从文件名获取
        if not song_name or not artist:
            filename = os.path.basename(file_path)
            filename_artist, filename_song = extract_info_from_filename(filename)
            
            if not artist:
                artist = filename_artist
                print(f"ID3标签中无艺术家，从文件名解析: {artist}")
            
            if not song_name:
                song_name = filename_song
                print(f"ID3标签中无歌曲名，从文件名解析: {song_name}")
        
        # 检查是否已有专辑封面
        if has_cover_art(audio):
            print(f"{os.path.basename(file_path)}: 已有专辑封面，跳过下载")
            # 如果有封面但需要重命名，则只执行重命名
            new_path = rename_file_with_date_prefix(file_path)
            return True
        
        # 下载封面和元数据
        print(f"开始下载专辑封面和元数据...")
        cover_data, metadata = download_cover(song_name, artist)
        
        # 如果获取到元数据，则更新ID3标签
        if metadata and (metadata.get('title') or metadata.get('artist') or metadata.get('album')):
            print(f"更新元数据: 标题={metadata.get('title', '')}, 艺术家={metadata.get('artist', '')}, 专辑={metadata.get('album', '')}")
            
            # 更新标题
            if metadata.get('title'):
                audio.add(TIT2(encoding=3, text=metadata['title']))
            
            # 更新艺术家
            if metadata.get('artist'):
                audio.add(TPE1(encoding=3, text=metadata['artist']))
            
            # 更新专辑
            if metadata.get('album'):
                audio.add(TALB(encoding=3, text=metadata['album']))
            
            # 保存更新后的标签
            audio.save()
            print(f"{os.path.basename(file_path)}: 成功更新元数据")
        
        # 如果找到了封面数据，则写入专辑封面
        if cover_data:
            # 写入封面
            print(f"写入专辑封面到文件...")
            audio.add(APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc=u'Cover',
                data=cover_data
            ))
            audio.save()
            print(f"{os.path.basename(file_path)}: 成功添加专辑封面")
        elif not has_cover_art(audio):
            print(f"{os.path.basename(file_path)}: 无法找到专辑封面(QQ音乐、网易云、酷狗和酷我音乐均无结果)")
            # 即使没有封面也继续处理（重命名等）
        
        # 重命名文件，添加当前日期前缀（YYYYMMDD.原文件名）
        new_path = rename_file_with_date_prefix(file_path)
        
        return True
        
    except Exception as e:
        print(f"{os.path.basename(file_path)}: 处理失败 - {str(e)}")
        return False

def batch_process_directory(directory, delay=0.5):
    success_count = 0
    failure_count = 0
    
    # 首先获取所有MP3文件的列表
    mp3_files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.mp3'):
            mp3_files.append(os.path.join(directory, filename))
    
    total_files = len(mp3_files)
    print(f"发现 {total_files} 个MP3文件需要处理")
    
    # 依次处理每个文件
    for index, file_path in enumerate(mp3_files):
        print(f"\n[{index+1}/{total_files}] 处理文件: {os.path.basename(file_path)}")
        if process_mp3_file(file_path):
            success_count += 1
        else:
            failure_count += 1
        
        # 添加延迟，避免频繁请求API
        if index < total_files - 1:
            time.sleep(delay)
    
    print(f"\n处理完成: 成功 {success_count} 个, 失败 {failure_count} 个")

if __name__ == "__main__":
    import argparse
    
    # 显示欢迎信息和版本号
    print("\nMP3专辑封面下载器 v1.0.0\n")
    
    # 显示使用说明
    show_usage_info()
    
    # 支持文件拖放
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]) and '--' not in sys.argv[1]:
        # 如果第一个参数是有效路径且不是选项，视为拖放
        drop_path = sys.argv[1]
        sys.argv = [sys.argv[0]] + ['--'] + sys.argv[1:]  # 添加分隔符，防止路径被当作选项
    
    parser = argparse.ArgumentParser(description='MP3专辑封面下载器')
    parser.add_argument('path', nargs='?', default='.', help='MP3文件或目录路径(默认为当前目录)')
    parser.add_argument('--delay', type=float, default=0.5, help='每首歌曲处理间隔时间(秒)，默认0.5秒')
    parser.add_argument('--no-rename', action='store_true', help='不重命名文件，仅添加封面')
    parser.add_argument('--force-download', action='store_true', help='即使已有封面也强制重新下载')
    parser.add_argument('--verbose', action='store_true', help='显示详细的处理信息')
    args = parser.parse_args()
    
    # 设置详细日志模式
    if not args.verbose:
        # 非详细模式下，覆盖print函数以过滤掉一些详细输出
        original_print = print
        def filtered_print(*args, **kwargs):
            # 过滤掉一些详细信息日志
            if args and isinstance(args[0], str):
                text = args[0]
                if any(x in text for x in ["获取到歌曲名", "获取到艺术家", "ID3标签中无", "开始处理", "开始下载", "写入专辑封面"]):
                    return
            original_print(*args, **kwargs)
        print = filtered_print
    
    # 如果不需要重命名文件，修改函数行为
    if args.no_rename:
        # 创建一个空函数替换原有的重命名函数
        def rename_file_with_date_prefix(file_path):
            return file_path
        print("已禁用文件重命名功能")
    
    # 如果强制下载，修改检查函数
    if args.force_download:
        def has_cover_art(audio):
            return False
        print("已启用强制下载模式，将重新下载所有MP3的封面")
    
    if os.path.isfile(args.path):
        process_mp3_file(args.path)
    elif os.path.isdir(args.path):
        print(f"开始批量处理目录: {args.path}")
        print(f"将搜索QQ音乐、网易云音乐、酷狗音乐和酷我音乐获取专辑封面")
        print(f"处理间隔设置为 {args.delay} 秒")
        batch_process_directory(args.path, args.delay)
    else:
        print("错误: 路径不存在")
    
    # 如果是打包后的程序，在结束时暂停
    if getattr(sys, 'frozen', False):
        print("\n处理完成，按任意键退出...")
        try:
            input()
        except:
            pass