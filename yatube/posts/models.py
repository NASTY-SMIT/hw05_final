from django.contrib.auth import get_user_model
from django.db import models
from core.models import CreatedModel

User = get_user_model()


class Group(models.Model):
    title = models.CharField("Название", max_length=200)
    slug = models.SlugField("Адрес", unique=True)
    description = models.TextField("Описание")

    def __str__(self):
        return self.title


class Post(CreatedModel):
    text = models.TextField("Текст поста", help_text='Введите текст поста')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name="Автор"
    )
    group = models.ForeignKey(
        Group,
        blank=True, null=True,
        on_delete=models.SET_NULL,
        related_name='posts',
        verbose_name="Группа",
        help_text='Группа, к которой будет относиться пост'
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return self.text[:15]


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE,
                             related_name='comments', verbose_name="Пост")
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='comments',
                               verbose_name='Автор')
    text = models.TextField(
        'Текст', help_text='Текст нового комментария')
    created = models.DateTimeField("Дата публикации коментария",
                                   auto_now_add=True)

    def __str__(self):
        return self.text


class Follow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='follower',
                             verbose_name='Подписчик')
    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='following',
                               verbose_name='Автор')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"],
                name="unique_follow",
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='check_not_self_follow'
            ),
        ]
