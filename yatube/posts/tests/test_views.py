from django.core.cache import cache
from django import forms
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Group, Post, User, Comment, Follow


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Name')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='Test')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            (reverse('posts:group_list', kwargs={'slug': self.group.slug})
             ): 'posts/group_list.html',
            (reverse('posts:profile', kwargs={'username': 'Test'})
             ): 'posts/profile.html',
            (reverse('posts:post_detail', kwargs={'post_id': '1'})
             ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_edit_template_name_exists_authorized(self):
        """URL-адрес /posts/2/edit/ использует соответствующий шаблон."""
        self.user_2 = User.objects.create_user(username='author')
        self.author = Client()
        self.author.force_login(self.user_2)
        Post.objects.create(
            text='Тестовый текст',
            author=self.user_2
        )
        response = self.author.get(
            reverse('posts:post_edit', kwargs={'post_id': '2'}))
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        expected = list(
            Post.objects.select_related('author', 'group').order_by(
                '-pub_date'))[:10]
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse('posts:group_list',
                    kwargs={'slug': self.group.slug})))
        expected = list(
            Post.objects.filter(group_id=self.group.id).order_by(
                '-pub_date'))[:10]
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.authorized_client.get(reverse('posts:profile',
                    kwargs={'username': self.user})))
        expected = list(
            Post.objects.filter(author_id=self.user.id).order_by(
                '-pub_date'))[:10]
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})))
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.assertEqual(response.context.get('post').image, self.post.image)

    def test_post_create_pages_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.ModelChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_pages_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        self.user_5 = User.objects.create_user(username='Тестировщик')
        self.author = Client()
        self.author.force_login(self.user_5)
        Post.objects.create(
            text='Тестовый текст',
            author=self.user_5,
            id='7'
        )
        response = self.author.get(reverse(
                                   'posts:post_edit', kwargs={'post_id': '7'}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.ModelChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_image_in_index_and_profile_page_and_group_and(self):
        """Картинка передается на страницу index_and_profile."""
        templates = [
            reverse('posts:index'),
            reverse("posts:profile", kwargs={'username': self.post.author}),
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        ]
        for url in templates:
            with self.subTest(url):
                response = self.authorized_client.get(url)
                first_object = response.context["page_obj"][0]
                self.assertEqual(first_object.image, self.post.image)

    def test_cache_index(self):
        """Проверка хранения и очищения кэша для index."""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(
            text='Еще пост',
            author=self.user,
        )
        response_old = self.authorized_client.get(reverse('posts:index'))
        old_posts = response_old.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_new = self.authorized_client.get(reverse('posts:index'))
        new_posts = response_new.content
        self.assertNotEqual(old_posts, new_posts)

    def test_following(self):
        """ Пользовтаель может подписываться на авторов и
        пост появляется в ленте тех, кто на него подписан"""
        count_follows = Follow.objects.count()
        self.user_6 = User.objects.create_user(username='Гена_Букин')
        self.follower = Client()
        self.follower.force_login(self.user_6)
        following = Follow.objects.create(user=self.user_6,
                                          author=PostPagesTests.user)
        response = (self.follower.get(
            reverse('posts:follow_index')))
        self.assertEqual((response.context['page_obj'].object_list),
                         list(following.author.posts.all()))
        self.assertEqual(Follow.objects.count(), count_follows + 1)

    def test_comment(self):
        """Комментировать может только залогиненный"""
        count_comments = Comment.objects.count()
        form_data = {'text': 'Комент'}
        response = (self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True))
        comment = Comment.objects.latest('id')
        self.assertEqual(Comment.objects.count(), count_comments + 1)
        self.assertEqual(comment.text, form_data['text'])
        self.assertRedirects(
            response, reverse('posts:post_detail', args={self.post.id})
        )

    def test_unfollowing(self):
        """ Пользовтаель может отписываться от авторов"""
        count_follows = Follow.objects.count()
        self.user_6 = User.objects.create_user(username='Гена_Букин')
        self.follower = Client()
        self.follower.force_login(self.user_6)
        Follow.objects.create(user=self.user_6,
                              author=PostPagesTests.user)
        (self.follower.get(
            reverse('posts:profile_unfollow', args={PostPagesTests.user})))
        self.assertEqual(Follow.objects.count(), count_follows)
