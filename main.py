import shutil
import time
from pathlib import Path
from dotenv import load_dotenv
import httpx
import telegram.error
from telegram import *
from telegram.ext import *
import os

load_dotenv()
files_not_transferred = []
files_transferred = []
start_time_scr = time.time()
parent_dir = '/home/sendilien/d/Media'
src_dir = '/run/user/1000/gvfs/mtp:host=SAMSUNG_SAMSUNG_Android_270c959535017ece/Phone/Pictures/Telegram'
tg_bot_token = os.getenv('TG_BOT_TOKEN')

actual_count_files = len(os.listdir(src_dir))
total_size_files_transferred = 0
count_files_transferred = 0


def get_dir_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total


actual_total_size_files = get_dir_size(src_dir)
path_transferred = Path('transferred.txt')
path_not_transferred = Path('not_transferred.txt')


async def move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global total_size_files_transferred, count_files_transferred, \
        actual_count_files, actual_total_size_files, files_transferred
    load_transferred_filenames()
    print(f'{os.path.exists(parent_dir)}')
    path = os.path.join(parent_dir, 'nottransferred')
    if not os.path.exists(path):
        os.mkdir(path)
    else:
        print(f"{path} already exists")

    for filename in os.listdir(src_dir):
        if filename not in files_transferred:
            print(f'moving file: {filename}')
            if os.path.exists(path + '/' + filename):
                continue
            shutil.copy(src_dir + '/' + filename, path + '/' + filename)
    print(f'Moved not transferred files to the following directory: {path}')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global total_size_files_transferred, count_files_transferred, \
        actual_count_files, actual_total_size_files, files_transferred

    if os.stat(path_transferred).st_size != 0:
        print(f'File not empty!')
        load_transferred_filenames()

    print('I started sending the docs...')
    await context.bot.send_message(chat_id=update.effective_chat.id, text='I started sending the docs...')

    print(f'actual total count of files is {actual_count_files}')
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f'actual total count of files is {actual_count_files}')
    print(f'actual total size of files is {actual_total_size_files / 1048576} MBs')
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f'actual total size of files is {actual_total_size_files / 1048576} MBs')

    print(f'{actual_count_files - len(files_transferred)} should be transferred.\n '
          f'Transferring will be started in 30 secs')
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f'{actual_count_files - len(files_transferred)} should be transferred.\n'
                                        f'Transferring will be started in 30 secs')

    print(f'\n')

    start_time = 0
    end_time = 0
    load_transferred_filenames()
    load_not_transferred_filenames()
    for filename in os.listdir(src_dir):
        if filename in files_transferred:
            if filename in files_not_transferred:
                files_not_transferred.remove(filename)
            continue
        try:
            if filename:
                count_files_transferred += 1
            start_time = time.time()
            src_file = os.path.join(src_dir, filename)
            await context.bot.send_document(
                chat_id=-1002000445219,
                document=src_file
            )

            end_time = time.time()

            print(f'duration of file ({filename[:10]}...) is {end_time - start_time}')
            current_file_size = os.path.getsize(src_file)  # in MBs
            current_speed = current_file_size / (end_time - start_time)
            print(f'the speed of file transferring : {current_speed} mb/s')

            total_size_files_transferred = total_size_files_transferred + current_file_size
            files_transferred.append(filename)
            if filename in files_not_transferred:
                files_not_transferred.remove(filename)
        except telegram.error.NetworkError:
            if filename in files_not_transferred:
                files_not_transferred.append(filename)
            print(f'Network Error occurred, I will sleep for 30 seconds and try again!')
            time.sleep(30)
        except telegram.error.RetryAfter as e:
            if filename in files_not_transferred:
                files_not_transferred.append(filename)
            print(f'Error occurred, I will sleep for {e.retry_after} seconds and try again!')
            time.sleep(e.retry_after)
        except httpx.RemoteProtocolError:
            upload_transferred_file_names()
            upload_not_transferred_file_names()
            time.sleep(30)
            print(f'Network Error occurred, I will sleep for 30 seconds and try again!')
        except Exception as e:
            upload_transferred_file_names()
            upload_not_transferred_file_names()
            time.sleep(30)
            print(f'Network Error occurred, I will sleep for 30 seconds and try again!')
        print(f'count_files_transferred {count_files_transferred}')
    print(f'\n')
    print(f'total size of files transferred is {total_size_files_transferred} MBs')
    upload_transferred_file_names()
    upload_not_transferred_file_names()
    end_time_scr = time.time()
    print(f'total duration of file transferred ({end_time_scr - start_time_scr}) seconds')

    if total_size_files_transferred != actual_total_size_files:
        print(f'In total {(actual_total_size_files - total_size_files_transferred) / 1048576} MBs wasnt transferred')

        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f'In total {(actual_total_size_files - total_size_files_transferred) / 1048576} '
                                            f'MBs of data wasnt transferred')

    if len(files_not_transferred) == 0:
        print(f'All the files were transferred successfully')
    else:
        print(f'A list of files that weren\'t transferred: {files_not_transferred}')


def load_transferred_filenames():
    global files_transferred
    files_transferred = []
    with open(path_transferred, 'r') as in_file:
        for line in in_file.readlines():
            files_transferred.append(line.rstrip())


def load_not_transferred_filenames():
    global files_not_transferred
    files_not_transferred = []
    with open(path_not_transferred, 'r') as in_file:
        for line in in_file.readlines():
            files_not_transferred.append(line.rstrip())


def upload_transferred_file_names():
    with open(path_transferred, 'w') as out_file:
        str = ''
        for filename in files_transferred:
            str += f'{filename}\n'
        out_file.write(str)


def upload_not_transferred_file_names():
    with open(path_not_transferred, 'w') as out_file:
        str = ''
        for filename in files_not_transferred:
            str += f'{filename}\n'
        out_file.write(str)


if __name__ == '__main__':
    application = (ApplicationBuilder().token()
                   .base_url("http://0.0.0.0:8081/bot")
                   .read_timeout(30)
                   .write_timeout(35)
                   .build())

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('move', move))
    application.run_polling()
    print(f'Mission Complete... You can order something for yourself!')
