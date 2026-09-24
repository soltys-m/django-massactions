from django.db import models


class ItemQuerySet(models.QuerySet):
    def active_only(self):
        return self.filter(is_active=True)


class Item(models.Model):
    STATUS = (('NEW', 'New'), ('DONE', 'Done'))

    name = models.CharField(max_length=50)
    status = models.CharField(max_length=10, choices=STATUS, default='NEW')
    note = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)

    objects = ItemQuerySet.as_manager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return '/items/%s/' % self.pk


class Child(models.Model):
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    label = models.CharField(max_length=50)

    def __str__(self):
        return self.label
