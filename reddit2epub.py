import json
import re
import sys
from typing import List

import click
import pkg_resources
import praw
from ebooklib import epub
from ebooklib.epub import EpubBook
from praw.reddit import Redditor, Subreddit, Submission

reddit = praw.Reddit(client_id="sUBJ9ERh2RyjmQ", client_secret=None,
                     user_agent='Reddit stories to epub by mircohaug')


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    infos = {
        "version": pkg_resources.get_distribution("reddit2epub").version
    }
    click.echo(json.dumps(infos))
    ctx.exit()


@click.command()
@click.option('input_url', '--input', '-i', required=True,
              help='The url of an arbitrary chapter of the series you want to convert')
@click.option('output_filename', '--output', '-o', default="",
              help='The filename of the output epub. Defaults to the first chapter title.')
@click.option('--overlap', default=2, help='How many common words do the titles have at the beginning.')
@click.option('--all-reddit/--no-all-reddit', default=False, help='Search over all reddit. '
                                                                  'Meant for stories which span subreddits')
@click.option('--version', help="Print version information and exit.", is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
def main(input_url: str, overlap: int, output_filename, all_reddit):
    author, selected_submissions, search_title = get_chapters_from_anchor(input_url, overlap, all_reddit)

    len_selected_submissions = len(selected_submissions)
    print("Total number of found posts with title prefix '{}' in subreddit: {}".format(search_title,
                                                                                       len_selected_submissions))

    len_subs = len(selected_submissions)
    print("Number of applicaple posts {}".format(len_subs))
    if len_subs == 1:
        raise Exception("No other chapters found, which share the first {} words with other posts from this "
                        "author in this subreddit.".format(overlap))
    elif len_subs == 0:
        raise Exception("No text chapters found")

    if len_selected_submissions >= 200:
        print("Got more than 200 submissions from author in this subreddit :-O. "
              "It may be possible that old chapters are not included.",
              file=sys.stderr)

    # Build the ebook

    # set metadata
    book_id = selected_submissions[-1].id
    book_title = selected_submissions[-1].title
    book_author = author.name

    book = create_book_from_chapters(book_author, book_id, book_title, selected_submissions)

    # replace all non alphanumeric chars through _ for filename sanitation
    if output_filename:
        file_name = output_filename
    else:
        file_name = (re.sub('[^0-9a-zA-Z]+', '_', book_title) + ".epub").strip("_OC")

    # write to the file
    epub.write_epub(file_name, book, {})


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


if __name__ == '__main__':
    main()
