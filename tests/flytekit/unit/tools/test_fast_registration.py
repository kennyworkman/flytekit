import tarfile

from flytekit.tools.fast_registration import filter_tar_file_fn, get_additional_distribution_loc


def testfilter_tar_file_fn():
    valid_tarinfo = tarfile.TarInfo(name="foo.py")
    assert filter_tar_file_fn(valid_tarinfo) is not None

    invalid_tarinfo = tarfile.TarInfo(name="foo.pyc")
    assert not filter_tar_file_fn(invalid_tarinfo)

    invalid_tarinfo = tarfile.TarInfo(name=".cache/foo")
    assert not filter_tar_file_fn(invalid_tarinfo)

    invalid_tarinfo = tarfile.TarInfo(name="__pycache__")
    assert not filter_tar_file_fn(invalid_tarinfo)


def test_get_additional_distribution_loc():
    assert get_additional_distribution_loc("s3://my-s3-bucket/dir", "123abc") == "s3://my-s3-bucket/dir/123abc.tar.gz"
