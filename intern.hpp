#ifndef INTERN_HPP
#define INTERN_HPP

#include <climits>
#include <functional>
#include <memory>
#include <mutex>
#include <tuple>
#include <unordered_map>
#include <utility>

namespace intern {

	//---- Hash Utilities ------------------------------------------------------
	//
	//	Hash(args...) -> std::size_t:
	//		This function hashes one or more args. std::hash is used to
	//		calculate a hash value on each arg. If there are multiple args,
	//		the hash values are combined into one.
	//
	//	HashTuple(arg) -> std::size_t:
	//		This function calls Hash() on its elements of a tuple-like arg
	//		(e.g. std::tuple, std::pair, std::array).

	template<typename T, typename... Ts>
		constexpr auto Hash(const T& v, const Ts&... vs) -> std::size_t {
			if constexpr(sizeof...(Ts) == 0) {
				return std::hash<T>{}(v);
			}
			else {
				//	The hash-combining algorithm was "boosted" from boost with
				//	one modification to extend the "magic" number to 64 bits
				//	where appropriate. (Also, the hashes are combined in the
				//	reverse order of the args for recursion's sake, not that
				//	it matters.)
				constexpr std::size_t kMagic =
					sizeof(std::size_t) * CHAR_BIT > 32u ?
					0x9e3779b97f4a7c15 : 0x9e3779b9;
				auto seed = Hash(vs...);
				return seed ^ (Hash(v) + kMagic + (seed << 6) + (seed >> 2));
			}
		}
	template<typename Tuple>
		constexpr auto HashTuple(const Tuple& tuple) {
			return std::apply(
				[](const auto&... args) { return Hash(args...); }, tuple
				);
		}

	//---- Internment ----------------------------------------------------------
	//
	//	MakeInterned<Cls,Tuple>(args...)
	//			-> std::shared_ptr<const Interned<Cls,Tuple>:
	//		Given a hashable and equality-comparable class (Cls), this function
	//		returns an interned shared pointer to an instance of it.

	template<class Cls, typename Tuple>
		class Interned: public Cls {
			template<class Cls2, typename Tuple2, typename... Args>
				friend auto MakeInterned(Args&&... args)
					-> std::shared_ptr<const Interned<Cls2,Tuple2>>;
			using TInternMap = std::unordered_map<
				const Interned*, std::weak_ptr<const Interned>
				>;
			using TInternMut = std::mutex;
			inline static TInternMap gInternMap;
			inline static TInternMut gInternMut;
		 public:
			using Cls::Cls;
			~Interned() {
					std::lock_guard<TInternMut> lg{gInternMut};
					gInternMap.erase(this);
				}
		};
	template<class Cls, typename Tuple=void, typename... Args>
		auto MakeInterned(Args&&... args)
			-> std::shared_ptr<const Interned<Cls,Tuple>>
		{
			using TInterned = Interned<Cls,Tuple>;
			using TMutex = typename TInterned::TInternMut;
			std::shared_ptr<const TInterned> p;
			TInterned val{std::forward<Args>(args)...};
			std::lock_guard<TMutex> lg{TInterned::gInternMut};
			auto& map = TInterned::gInternMap;
			auto it = map.find(&val);
			if(it == map.end()) {
				p = std::make_shared<const TInterned>(std::move(val));
				map.insert(it, std::make_pair(p.get(), p));
			}
			else {
				p = it->second.lock();
			}
			return std::move(p);
		}
}

namespace std {
	template<typename Cls, typename Tuple>
		struct hash<const intern::Interned<Cls,Tuple>*> {
			auto operator()(
				const intern::Interned<Cls,Tuple>* p)
					const noexcept -> std::size_t
				{
					return intern::HashTuple(static_cast<Tuple>(*p));
				}
		};
	template<typename Cls>
		struct hash<const intern::Interned<Cls,void>*> {
			auto operator()(
				const intern::Interned<Cls,void>* p)
					const noexcept -> std::size_t
				{
					return hash<Cls>{}(*p);
				}
		};
}

#endif
