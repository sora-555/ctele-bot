from html import escape
def result_card(query,item,index,page,total=None):
 count=f'Result {index} of {total}' if total else f'Result {index} · Source page {page}'
 return f'❖ Search · {escape(query)}\n━━━━━━━━━━━━━━━━━━━━\n\n<b>{escape(item.title)}</b>\n\n▸ {count}\n\nMedia is automatically removed after 30 minutes.'
def gallery_caption(post,index): return f'❖ <b>{escape(post.title)}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n▸ Image {index} of {len(post.images)}\n▸ Automatically removed after 30 minutes'
