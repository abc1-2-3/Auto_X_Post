from TestXPost import upload_and_post
from TestContent import pick_topic, generate_img


if __name__ == "__main__":
    sentence=pick_topic()
    img=generate_img(sentence)
    upload_and_post(sentence, img)