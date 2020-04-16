from typing import List

import praw
from ebooklib import epub
from ebooklib.epub import EpubBook
from praw.reddit import Redditor, Submission, Subreddit

reddit = praw.Reddit(client_id="sUBJ9ERh2RyjmQ", client_secret=None,
                     user_agent='Reddit stories to epub by mircohaug')

def get_chapters_from_anchor(
        input_url,
        overlap: int = 2,
        all_reddit: bool = False,
) -> (Redditor, List[Submission], str):
    author, post_subreddit, title = process_anchor_url(input_url)

    search_title = " ".join(title.split(" ")[:overlap])

    selected_submissions = get_selected_posts(author=author,
                                              post_subreddit=post_subreddit,
                                              all_reddit=all_reddit,
                                              search_title=search_title)
    return author, selected_submissions, search_title


def create_book_from_chapters(
        book_author: str,
        book_id: str,
        book_title: str,
        reddit_chapters: List[Submission]) -> EpubBook:
    book = epub.EpubBook()
    book.set_identifier(book_id)
    book.set_title(book_title)
    book.add_author(book_author)
    book.set_language('en')
    cover = epub.EpubHtml(title=book_title, file_name='cover.xhtml', lang='en')
    cover.content = "<div><h1>{0}</h1>" \
                    "<h2><a href=\"https://www.reddit.com/user/{1}\">{1}</a></h2>" \
                    "{2}</div>".format(book_title, book_author,
                                       "Created with the reddit2epub python package")
    book.add_item(cover)
    book_chapters = []
    print("Chapters:")
    # check for title prefix
    for i, sub in enumerate(reversed(reddit_chapters)):
        # create chapter
        c1 = epub.EpubHtml(title=sub.title, file_name='chap_{}.xhtml'.format(i), lang='en')
        c1.content = """<h1>{0}</h1>
                     <a href="{1}">Original</a>
                     {2}
                     <a href="{1}">Original</a>
                     """.format(sub.title, sub.shortlink, sub.selftext_html)

        # add chapter
        book.add_item(c1)
        book_chapters.append(c1)

        print(sub.title)
    # define Table Of Contents
    book.toc = (
        book_chapters
    )
    # add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    # basic spine
    spine = [cover, 'nav']
    spine.extend(book_chapters)
    # is used to generate the toc at the start
    book.spine = spine
    return book


def get_selected_posts(
        author: Redditor,
        post_subreddit: Subreddit,
        search_title: str,
        all_reddit: bool = False,
) -> List[Submission]:
    if all_reddit:
        sub_to_search_in = reddit.subreddit('all')
    else:
        sub_to_search_in = post_subreddit
    # is limited to 250 items
    list_of_posts = sub_to_search_in.search("author:\"{}\" title:\"{}\" ".format(author, search_title), limit=None,
                                            sort='new')
    list_of_posts = list(list_of_posts)
    selected_submissions = []
    for p in list_of_posts:
        # starting with the same words
        if p.title.startswith(search_title) and isinstance(p, Submission):
            if p.is_self:
                selected_submissions.append(p)
            else:
                # is crosspost if not likely media and ignored
                if hasattr(p, "crosspost_parent"):
                    original_post = list(reddit.info(fullnames=[p.crosspost_parent]))[0]
                    if not original_post.is_self:
                        # double crossposts not supported
                        continue
                    else:
                        if isinstance(original_post, Submission):
                            selected_submissions.append(original_post)
    return selected_submissions


def process_anchor_url(input_url: str) -> (Redditor, Subreddit, str):
    initial_submission = reddit.submission(url=input_url)
    title = initial_submission.title
    author = initial_submission.author
    post_subreddit = initial_submission.subreddit
    return author, post_subreddit, title