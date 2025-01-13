"""Downloads media from telegram."""
import asyncio
import logging
import os
from typing import List, Optional, Tuple, Union

import pyrogram
import yaml
from pyrogram.types import Audio, Document, Photo, Video, VideoNote, Voice
from rich.logging import RichHandler
from tqdm import tqdm

from utils.file_management import get_next_name, manage_duplicate_file
from utils.log import LogFilter
from utils.meta import print_meta
from utils.updates import check_for_updates

# Configure logging to show only important messages
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(show_path=False, show_time=False)]
)

# Filter out pyrogram's internal logs
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pyrogram.session.session").addFilter(LogFilter())
logging.getLogger("pyrogram.client").addFilter(LogFilter())
logger = logging.getLogger("media_downloader")

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FAILED_IDS: list = []
DOWNLOADED_IDS: list = []

MAX_CONCURRENT_DOWNLOADS = 4  # Number of concurrent downloads
CHUNK_SIZE = 2097152  # 2MB chunks for faster downloads

def update_config(config: dict):
    """
    Update existing configuration file.

    Parameters
    ----------
    config: dict
        Configuration to be written into config file.
    """
    config["ids_to_retry"] = (
        list(set(config["ids_to_retry"]) - set(DOWNLOADED_IDS)) + FAILED_IDS
    )
    with open("config.yaml", "w") as yaml_file:
        yaml.dump(config, yaml_file, default_flow_style=False)
    logger.info("Updated last read message_id to config file")


def _can_download(_type: str, file_formats: dict, file_format: Optional[str]) -> bool:
    """
    Check if the given file format can be downloaded.

    Parameters
    ----------
    _type: str
        Type of media object.
    file_formats: dict
        Dictionary containing the list of file_formats
        to be downloaded for `audio`, `document` & `video`
        media types
    file_format: str
        Format of the current file to be downloaded.

    Returns
    -------
    bool
        True if the file format can be downloaded else False.
    """
    if _type in ["audio", "document", "video"]:
        allowed_formats: list = file_formats[_type]
        if not file_format in allowed_formats and allowed_formats[0] != "all":
            return False
    return True


def _is_exist(file_path: str) -> bool:
    """
    Check if a file exists and it is not a directory.

    Parameters
    ----------
    file_path: str
        Absolute path of the file to be checked.

    Returns
    -------
    bool
        True if the file exists else False.
    """
    return not os.path.isdir(file_path) and os.path.exists(file_path)


def _get_safe_channel_name(message: pyrogram.types.Message) -> str:
    """Get a safe channel name for folder creation.

    Parameters
    ----------
    message: pyrogram.types.Message
        Message object from which to extract channel name.

    Returns
    -------
    str
        Safe channel name for folder creation.
    """
    chat = message.chat
    if chat.title:
        # Remove invalid characters from channel name
        channel_name = "".join(c for c in chat.title if c.isalnum() or c in (' ', '-', '_'))
        return channel_name.strip()
    return "unknown_channel"


async def _get_media_meta(
    media_obj: Union[Audio, Document, Photo, Video, VideoNote, Voice],
    _type: str,
    message: pyrogram.types.Message,
    download_dir: str,
) -> Tuple[str, Optional[str]]:
    """Extract file name and file id from media object.

    Parameters
    ----------
    media_obj: Union[Audio, Document, Photo, Video, VideoNote, Voice]
        Media object to be extracted.
    _type: str
        Type of media object.
    message: pyrogram.types.Message
        Message object containing the media.
    download_dir: str
        Custom directory to save downloaded files

    Returns
    -------
    Tuple[str, Optional[str]]
        file_name, file_format
    """
    if _type in ["audio", "document", "video"]:
        file_format: Optional[str] = media_obj.mime_type.split("/")[-1]  # type: ignore
    else:
        file_format = None

    channel_name = _get_safe_channel_name(message)
    channel_dir = os.path.join(download_dir, channel_name)
    
    # Create channel directory if it doesn't exist
    os.makedirs(channel_dir, exist_ok=True)
    
    if _type in ["voice", "video_note"]:
        file_format = media_obj.mime_type.split("/")[-1]  # type: ignore
        file_name: str = os.path.join(
            channel_dir,
            _type,
            "{}_{}.{}".format(
                _type,
                media_obj.date.isoformat(),  # type: ignore
                file_format,
            ),
        )
    else:
        file_name = os.path.join(
            channel_dir, _type, getattr(media_obj, "file_name", None) or ""
        )
    
    # Create media type subdirectory
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    return file_name, file_format


def progress_callback(current: int, total: int, progress_bar: tqdm):
    """Callback function to update the progress bar.

    Parameters
    ----------
    current: int
        Current amount of bytes downloaded
    total: int
        Total size of the file in bytes
    progress_bar: tqdm
        Progress bar object to be updated
    """
    if total != 0:
        progress_bar.total = total
        progress_bar.update(current - progress_bar.n)


async def _download_media(
    client: pyrogram.Client,
    message: pyrogram.types.Message,
    media_types: List[str],
    file_formats: dict,
    download_dir: str,
) -> Optional[str]:
    """
    Download media from Telegram.

    Parameters
    ----------
    client: pyrogram.Client
        Client to interact with Telegram.
    message: pyrogram.types.Message
        Message object from telegram.
    media_types: list
        List of media types to be downloaded.
    file_formats: dict
        Dictionary containing the list of file_formats to be downloaded.
    download_dir: str
        Custom directory to save downloaded files

    Returns
    -------
    Optional[str]
        Downloaded file path or None if download failed.
    """
    try:
        if message.media is None:
            return None
        
        for _type in media_types:
            _media = getattr(message, _type, None)
            if _media is None:
                continue
            file_name, file_format = await _get_media_meta(_media, _type, message, download_dir)
            if _can_download(_type, file_formats, file_format):
                # Get file size if available
                file_size = getattr(_media, 'file_size', 0)
                desc = f"Downloading {os.path.basename(file_name)}"
                
                with tqdm(
                    total=file_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=desc,
                    dynamic_ncols=True
                ) as progress_bar:
                    if _is_exist(file_name):
                        file_name = get_next_name(file_name)
                        download_path = await client.download_media(
                            message,
                            file_name=file_name,
                            progress=lambda current, total: progress_callback(current, total, progress_bar)
                        )
                        download_path = manage_duplicate_file(download_path)  # type: ignore
                    else:
                        download_path = await client.download_media(
                            message,
                            file_name=file_name,
                            progress=lambda current, total: progress_callback(current, total, progress_bar)
                        )
                    
                    if download_path:
                        logger.info("Media downloaded - %s", download_path)
                    DOWNLOADED_IDS.append(message.id)
        return file_name
        
    except Exception as e:
        logger.error("Error downloading media: %s", str(e))
        FAILED_IDS.append(message.id)
        return None


async def process_messages(
    client: pyrogram.Client,
    messages: list,
    media_types: List[str],
    file_formats: dict,
    download_dir: str,
) -> int:
    """
    Process the messages and download media.

    Parameters
    ----------
    client: pyrogram.Client
        Client to interact with Telegram.
    messages: list
        List of telegram messages.
    media_types: list
        List of media types to be downloaded.
    file_formats: dict
        Dictionary containing the list of file_formats to be downloaded.
    download_dir: str
        Custom directory to save downloaded files

    Returns
    -------
    int
        Last processed message id.
    """
    last_message_id = None
    tasks = []
    
    for message in messages:
        if last_message_id is None:
            last_message_id = message.id
        tasks.append(
            _download_media(
                client=client,
                message=message,
                media_types=media_types,
                file_formats=file_formats,
                download_dir=download_dir
            )
        )
        
    # Process downloads in batches to avoid memory issues
    batch_size = MAX_CONCURRENT_DOWNLOADS
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i + batch_size]
        await asyncio.gather(*batch)
    
    return last_message_id


async def begin_import(config: dict, pagination_limit: int, channel_input: str = None, download_dir: str = None) -> dict:
    """
    Create pyrogram client and initiate download.

    Parameters
    ----------
    config: dict
        Dict containing the config to create pyrogram client.
    pagination_limit: int
        Number of message to download asynchronously as a batch.
    channel_input: str, optional
        Channel username or ID provided externally (e.g., from GUI)
    download_dir: str, optional
        Custom directory to save downloaded files

    Returns
    -------
    dict
        Updated configuration to be written into config file.
    """
    if not download_dir:
        download_dir = os.path.join(THIS_DIR, "downloads")
    
    # Ensure download directory exists
    os.makedirs(download_dir, exist_ok=True)
    
    global FAILED_IDS, DOWNLOADED_IDS
    FAILED_IDS = []
    DOWNLOADED_IDS = []
    
    try:
        async with pyrogram.Client(
            "media_downloader",
            api_id=config["api_id"],
            api_hash=config["api_hash"],
            phone_number=config["phone_number"],
        ) as client:
            if not channel_input:
                channel_input = _get_channel_id_from_input()
            
            channel_input = _clean_channel_input(channel_input)
            
            messages = []
            last_read_message_id = config.get("last_read_message_id", 0)
            messages_iter = client.get_chat_history(
                chat_id=channel_input,
                offset_id=last_read_message_id,
            )
            
            async for message in messages_iter:
                if message.id <= last_read_message_id:
                    break
                messages.append(message)
                
                if len(messages) >= pagination_limit:
                    last_read_message_id = await process_messages(
                        client=client,
                        messages=messages,
                        media_types=config["media_types"],
                        file_formats=config["file_formats"],
                        download_dir=download_dir
                    )
                    messages = []
                    
            if messages:
                last_read_message_id = await process_messages(
                    client=client,
                    messages=messages,
                    media_types=config["media_types"],
                    file_formats=config["file_formats"],
                    download_dir=download_dir
                )
            
            # Calculate totals
            total_downloaded = len(DOWNLOADED_IDS)
            total_failed = len(FAILED_IDS)
            
            # Show completion message
            if total_downloaded > 0 or total_failed > 0:
                logger.info("-" * 50)
                logger.info("Download Summary:")
                logger.info("✅ Successfully downloaded: %d files", total_downloaded)
                if total_failed > 0:
                    logger.info("❌ Failed downloads: %d files", total_failed)
                logger.info("-" * 50)
        
    except Exception as e:
        logger.error("Error occurred while downloading media: %s", str(e))
        
    return config


def _get_channel_id_from_input() -> str:
    """Get channel username or ID from user input.

    Returns
    -------
    str
        Channel username or ID entered by user.
    """
    print("\nEnter channel details:")
    print("1. For public channels: Enter channel username (without @)")
    print("2. For private channels: Enter channel ID (must be member)")
    channel_input = input("\nEnter channel username/ID: ").strip()
    return channel_input


def _clean_channel_input(channel_input: str) -> str:
    """Clean and format channel input.

    Parameters
    ----------
    channel_input: str
        Raw channel input from user

    Returns
    -------
    str
        Cleaned channel input
    """
    # Remove any whitespace
    channel_input = channel_input.strip()
    
    # Remove @ if present
    if channel_input.startswith('@'):
        channel_input = channel_input[1:]
    
    # Handle -100 prefix for channel IDs
    if channel_input.startswith('-100'):
        channel_input = channel_input[4:]
    elif channel_input.startswith('-'):
        channel_input = channel_input[1:]
    
    return channel_input


def main():
    """Main function of the downloader."""
    with open(os.path.join(THIS_DIR, "config.yaml")) as f:
        config = yaml.safe_load(f)
    updated_config = asyncio.get_event_loop().run_until_complete(
        begin_import(config, pagination_limit=100)
    )
    if FAILED_IDS:
        logger.info(
            "Downloading of %d files failed. "
            "Failed message ids are added to config file.\n"
            "These files will be downloaded on the next run.",
            len(set(FAILED_IDS)),
        )
    update_config(updated_config)
    check_for_updates()


if __name__ == "__main__":
    print_meta(logger)
    main()
