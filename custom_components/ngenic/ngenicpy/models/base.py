"""A module for base classes in NgenicPy."""

import json
import logging
from typing import Any

import httpx

from ..const import API_URL  # noqa: TID252
from ..exceptions import ApiException, ClientException  # noqa: TID252

LOG = logging.getLogger(__package__)

try:
    from time import monotonic
except ImportError:
    from time import time as monotonic


class NgenicBase:
    """Superclass for all models."""

    def __init__(
        self, session: httpx.AsyncClient = None, json_data: dict[str, Any] | None = None
    ) -> None:
        """Initialize our base object.

        :param session:
            (required) httpx client
        :param json_data:
            (required) Json representation of the concrete model
        """

        # store the httpx session on each object so we can reuse the connection
        self._session = session

        # backing json of the model
        self._json = json_data

        # poor-man's cache for get requests
        self._cache = {}

    def json(self) -> dict[str, Any]:
        """Get a json representaiton of the model.

        :return:

        """
        return self._json

    def uuid(self) -> str:
        """Get uuid attribute."""
        return self["uuid"]

    def __setitem__(self, attribute: str, data: Any):
        """Set an attribute in the model's JSON representation.

        :param attribute:
            (required) The attribute to set in the JSON representation
        :param data:
            (required) The data to set in the JSON representation
        """
        self._json[attribute] = data

    def __getitem__(self, attribute: str) -> Any:
        """Get an attribute from the model's JSON representation.

        :param attribute:
            (required) The attribute to get from the JSON representation
        :return:
            The value of the attribute
        :raises AttributeError:
            If the attribute is not found in the JSON representation
        """
        if attribute not in self._json:
            raise AttributeError(attribute)
        return self._json[attribute]

    def update(self) -> None:
        """Raise an exception as update is not allowed."""
        raise ClientException(f"Cannot update a '{self.__class__.__name__}'")

    def _parse(self, response: httpx.Response) -> Any:
        rsp_json = None

        if response is None:
            return None

        if response.status_code == 204:
            return None

        try:
            rsp_json = response.json()
        except ValueError:
            raise ApiException(
                f"Ngenic API return an invalid json body (status={response.status_code})",
            ) from ValueError

        return rsp_json

    def _new_instance(
        self, instance_class: type, json_data: Any, **kwargs
    ) -> type | list[type] | None:
        """Create a new model instance.

        :param class instance_class:
            (required) class of instance to initialize with jsosn
        :param dict json_data:
            (required) data to initialize the instance with
        :param kwargs:
            Additional data required by the instance type
        :return:
            new `instance_class` or `list(instance_class)`
        """
        if json_data is not None and (
            not isinstance(json_data, dict) and not isinstance(json_data, list)
        ):
            raise ClientException(
                "Invalid data to create new instance with (expected json)"
            )
        if not json_data:
            return None

        if isinstance(json_data, list):
            return [
                instance_class(session=self._session, json_data=inst_json, **kwargs)
                for inst_json in json_data
            ]
        return instance_class(self._session, json_data, **kwargs)

    async def _async_parse_new_instance(
        self, url: str, instance_class: type, **kwargs
    ) -> type | list[type] | None:
        """Get JSON from an URL and create a new instance of it.

        :param str url:
            (required) url to get instance data from
        :param type instance_class:
            (required) class of instance to initialize with parsed data
        :param kwargs:
            may contain additional args to the instance class
        :return:
            new `instance_class`
        :rtype:
            `instance_class`
        """
        ret_json = self._parse(await self._async_get(url))
        return self._new_instance(instance_class, ret_json, **kwargs)

    async def _async_request(
        self, method: str, url: str, is_retry: bool, *args, **kwargs
    ) -> httpx.Response:
        """Make a HTTP request (async).

        This is the generic method for all requests, it will handle errors etc in a common way.

        :param str method:
            (required) HTTP method (i.e get, post, delete)
        :param bool is_retry:
            Indicator if this execution is a retry.
            This is a temporary fix for retrying broken connections.
        :param args:
            Additional args to requests lib
        :param kwargs:
            Additional kwargs to requests lib
        :return:
            response
        """

        LOG.debug("%s %s with %s %s", method.upper(), url, args, kwargs)

        res: httpx.Response | None = None
        try:
            if not isinstance(self._session, httpx.AsyncClient):
                raise TypeError("Cannot use async methods when context is sync")  # noqa: TRY301

            request_method = getattr(self._session, method)
            res = await request_method(url, *args, **kwargs)

            # raise for e.g. 401
            res.raise_for_status()

            return res  # noqa: TRY300
        except httpx.CloseError as exc:
            if is_retry:
                # only retry once
                raise ClientException(
                    self._get_error("A request exception occurred", res, parent_ex=exc)
                ) from exc
            # retry request
            LOG.debug(
                "Got a CloseError while trying to send request. Retry request once."
            )
            return await self._async_request(method, url, True, *args, **kwargs)
        except httpx.HTTPError as exc:
            raise ClientException(
                self._get_error("A request exception occurred", res, parent_ex=exc)
            ) from exc
        except Exception as exc:
            raise ClientException(
                self._get_error("An exception occurred", res, parent_ex=exc)
            ) from exc

    def _get_error(
        self, msg: str, res: httpx.Response, parent_ex: Exception | None = None
    ):
        if res is not None and res.status_code == 429:
            # Too many requests
            server_msg = f"Too many requests have been made, retry again after {res.headers["X-RateLimit-Reset"]}"
        else:
            try:
                server_msg = res.json()["message"]
            except:  # noqa: E722
                if res is not None:
                    server_msg = str(res.status_code)
                elif parent_ex is not None:
                    if isinstance(parent_ex, httpx.ConnectTimeout):
                        server_msg = "Timed out connecting to ngenic server"

                    elif isinstance(parent_ex, httpx.ConnectTimeout):
                        server_msg = "Timed out sending request to ngenic server"
                    else:
                        server_msg = str(parent_ex)
                else:
                    server_msg = "Unknown error"

        return f"{msg}: {server_msg}"

    def _prehandle_write(self, data: Any, is_json: bool, **kwargs):
        headers = {}

        if is_json:
            data = json.dumps(data) if data is not None else data
            headers["Content-Type"] = "application/json"

        if "headers" in kwargs:
            # let caller override headers
            headers.update(kwargs.get("headers"))

        return (data, headers)

    def _async_delete(self, url: str):
        return self._async_request("delete", f"{API_URL}/{url}", False)

    async def _async_get(self, url: str):
        url = f"{API_URL}/{url}"
        now = monotonic()
        cache_key = hash(url)

        if cache_key in self._cache:
            expiration, result = self._cache[cache_key]
            if expiration > now:
                LOG.debug("Cache hit for %s", url)
                return result

        result = await self._async_request("get", url, False)

        expiration = now + 5.0
        self._cache[cache_key] = expiration, result

        return result

    def _async_post(self, url: str, data: Any = None, is_json: bool = True, **kwargs):
        data, headers = self._prehandle_write(data, is_json, kwargs)
        return self._async_request(
            "post", f"{API_URL}/{url}", False, data=data, headers=headers
        )

    def _async_put(self, url: str, data: Any = None, is_json: bool = True, **kwargs):
        data, headers = self._prehandle_write(data, is_json, **kwargs)
        return self._async_request(
            "put", f"{API_URL}/{url}", False, data=data, headers=headers
        )
