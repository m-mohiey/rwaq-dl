import requests
import os
from bs4 import BeautifulSoup as bs
from urllib.request import quote
import urllib.parse as parse
from pytube import YouTube
from tqdm import tqdm
import argparse
from colorama import *

# Initiation for colorama module to use colors in console
init()

# Initiate Argument Parser

parser = argparse.ArgumentParser(prog='rwaq-dl',description='rwaq-dl is a command line utility to download full courses from Rwaq.org')
#parser.add_help = 'rwaq-dl is a command line utility to download full courses from Rwaq.org'
parser.add_argument('-u','--user',required=True,help='User name like someone@gmail.com')
parser.add_argument('-p','--password',required=True,help='Password like password123')
parser.add_argument('-c','--course',required=True,help='Course Url like https://www.rwaq.org/courses/econometrics/sections')
parser.add_argument('-f','--folder',required=True,help='The folder to download the course to (please note it will be created if not exist) like C:/Courses')

args = parser.parse_args()

# setting basic parameters that going to be passed through command line arguments
user=quote(args.user)
password=quote(args.password)
course=args.course
download_folder=args.folder

# Functions definitions

# Error printing function

def print_error(msg):
    print(Fore.WHITE + Back.RED + Style.BRIGHT + '[rwaq-dl::ERROR]' + Style.RESET_ALL + ' ' + msg)
    exit(1)

# Warning printing function

def print_warning(msg):
    print(Fore.LIGHTWHITE_EX + Back.YELLOW + Style.BRIGHT + '[rwaq-dl::INFO]' + Style.RESET_ALL + ' ' + msg)


# Info printing function

def print_info(msg):
    print(Fore.WHITE + Back.GREEN + Style.BRIGHT + '[rwaq-dl::SUCCESS]' + Style.RESET_ALL + ' ' + msg)

# Login function that setup the session

def login(user,password,login_url='https://www.rwaq.org/users/sign_in'):
    session = requests.session()
    print_warning('Trying to Sign in')
    try:
        loged=session.post(login_url,data='user%5Bemail%5D={}&user%5Bpassword%5D={}'.format(user,password))
        if 'users/sign_in' in loged.url:
            print_error('Login Failed (wrong user name or password)')
            exit(1)

        print_info('Logged in Successfully')
        return session

    except requests.exceptions.RequestException as e:
        print_error( 'Login Failed (' + str(e) + ')')


# Validate course url function to make sure it is the right page

def validate_course(course):
    try:
        parsed=parse.urlsplit(course)
        if parsed.netloc == 'www.rwaq.org':
            if 'courses' == parsed.path.split('/')[1]:
                print_warning('Started with ' + course)
                return parse.urljoin(course, 'sections')
            else:
                print_error('Invalid Url (Not a course url)')
                return course
        else:
            print_error('Not rwaq.org course')

    except Exception as e:
        print_error('Invalid Url (' + str(e) + ')')
        return course


# check download folder function

def check_folder(download_folder):
    try:
        if os.path.exists(download_folder):
            if os.path.isdir(download_folder):
                print_warning('Download Folder Exists ' + download_folder + ' will be used')
            else:
                print_error('Invalid Download Folder')

        else:
            print_warning('Directory not found - Will create it')
            os.makedirs(download_folder)
            print_info(download_folder + ' created successfully')
        os.chdir(download_folder)
    except Exception as e:
        print_error('Cannot create download folder (' + str(e) + ')')


# get Course Title function

def get_title(soup):
    try:
        #soup = bs(soup,'lxml')
        return soup.select_one('h2.subject-title').text.strip()
    except Exception as e:
        print_error('Cannot get course title (' + str(e) + ')')

# get Course sections function

def get_sections(soup):
    try:
        #soup = bs(soup,'lxml')
        return soup.select('div.curriculum li.curriculum-section')
    except Exception as e:
        print_error('Cannot get course title (' + str(e) + ')')

# get Course items function

def get_items(soup):
    try:
        #soup = bs(soup,'lxml')
        return soup.select('ul.curriculum-section-content li.clearfix')
    except Exception as e:
        print_error('Cannot get course title (' + str(e) + ')')


# setting course folder function

def course_folder(course_title, download_folder=os.getcwd()):
    try:
        check_folder(os.path.join(download_folder,course_title))
        return os.path.join(download_folder,course_title)
    except Exception as e:
        print_error('Cannot use ' + course_title + ' as a download folder (' + str(e) + ')')


# getting and downloading items function

def get_item_contents(session,item_url,item_type,item_folder):
    try:
        response = session.get(item_url)
        soup = bs(response.text,'lxml')
        if 'play' in item_type:
            youtube_url = 'https://www.youtube.com/watch?v=' + parse.urlparse(soup.select_one('div.course-content iframe')['src']).path.split('/')[-1]
            yt = YouTube(youtube_url)
            video_url = yt.streams.filter(progressive=True).order_by('resolution').desc().first().url
            video_filename = yt.streams.filter(progressive=True).order_by('resolution').desc().first().default_filename
            download_file(session,video_url,item_folder,video_filename)
            #pass
        elif 'file' in item_type:
            body = soup.select_one('div.course-content div.lecture_desc').text
            with open(os.path.join(item_folder,soup.title.text + '.txt'),'w') as f:
                f.write(body)
            attachments = soup.select('div.course-content div.attached-files a.tool-tip')
            for attachment in attachments:
                #print(attachment)
                download_file(session,attachment['href'],item_folder,attachment['title'])
            #pass
        elif 'list' in item_type:
            with open(os.path.join(item_folder,soup.title.text + '.html'),'wb') as f:

                f.write(response.content)
            #pass
        else:
            print_warning('Unrecognized item type')

    except requests.exceptions.RequestException as e:
        print_warning('Invalid item url (' + str(e) + ')')
    except Exception as e:
        print_warning('Cannot download item (' + str(e) + ')')


# file download function

def download_file(session,url,folder,file_name):
    try:
        res = session.get(url, stream=True)
        chunk_size = 1024*1024
        #file_name = res.headers.get('content-disposition').replace('attachment;filename="', '').replace('"', '')
        print_warning('Now Downloading ' + file_name + ' in ' + folder)
        with open(os.path.join(folder, file_name), 'wb') as f:
            for chunck in tqdm(res.iter_content(chunk_size),
                               total=int(res.headers.get('content-length', 0)) / chunk_size, unit='MB', unit_scale=True,
                               desc='Now Downloading ' + file_name):
                if chunck:
                    f.write(chunck)
        print_info(file_name + ' Finished downloading successfully.')
    except requests.exceptions.RequestException as e:
        print_warning('Cannot Download File: (' + str(e) + ')')
    except Exception as e:
        print_warning('Cannot Download File: (' + str(e) + ')')



# Main

if __name__ == '__main__':
    session = login(user,password)
    course=validate_course(course)
    check_folder(download_folder)
    try:
        response = session.get(course)
        soup = bs(response.text,'lxml')
        course_dir = course_folder( get_title(soup), download_folder)
        section_count = 0
        for section in get_sections(soup):
            section_count += 1
            section_title = section.select_one('div.section-title ').text.strip()
            print_warning('Now working on ' + section_title)
            section_folder = os.path.join(course_dir,'{number:02}- '.format(number=section_count) + section_title)
            if not os.path.exists(section_folder):
                os.mkdir(section_folder)
            item_count = 0
            for item in get_items(section):
                item_count += 1
                item_title = item.select_one('span.row-title').text.strip()
                item_url = parse.urljoin(course,item.select_one('a')['href'])
                item_type = item.select_one('span.row-icon i.site-icons')['class'][0]
                item_folder = os.path.join(section_folder,'{number:02}- '.format(number=item_count) + item_title)
                print_warning('Now working on ' + item_title)
                #print_warning(item_type)
                if not os.path.exists(item_folder):
                    os.mkdir(item_folder)
                get_item_contents(session,item_url,item_type,item_folder)
                print_info('Finished ' + item_title)
            print_info('Finished ' + section_title)


    except requests.exceptions.RequestException as e:
        print_error('Cannot access course link (' + str(e) + ')')
    except Exception as e:
        print_error('Error (' + str(e) + ')')



